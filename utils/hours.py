
import os
import json
from datetime import time, timedelta, datetime
from zoneinfo import ZoneInfo

from flask import current_app as app
import botocore

from utils.rtsp import RTSPStreamInfo, KVSHandler
from clients import scheduler, subnets

def convert_from_UTC(time_to_convert, tz):
    tz = ZoneInfo(tz)
    utc = ZoneInfo('UTC')
    return time_to_convert.replace(tzinfo=utc).astimezone(tz)

def convert_to_UTC(time_to_convert, tz):
    tz = ZoneInfo(tz)
    utc = ZoneInfo('UTC')
    return time_to_convert.replace(tzinfo=tz).astimezone(utc)

class SingleRun:
    def __init__(self, start_time, duration):

        self.start_time = time.fromisoformat(start_time)
        if duration > 24:
            raise Exception('Invalid duration amount')
        self.duration = timedelta(hours=duration)

    def does_not_overlap_with(self, next, same_day):
        start = datetime.fromisoformat(
            self.start_time.strftime("2023-07-08 %H:%M:%S")
        )
        end = start + self.duration

        if same_day:
            next_time = datetime.fromisoformat(
                next.start_time.strftime("2023-07-08 %H:%M:%S")
            )
            return end < next_time
        
        else:
            next_time = datetime.fromisoformat(
                next.start_time.strftime("2023-07-09 %H:%M:%S")
            )
            return end < next_time
        
    def is_operational_at(self, timestamp, same_day):
        if same_day:
            start = datetime.fromisoformat(
                self.start_time.strftime(f"{timestamp.year}-{timestamp.month}-{timestamp.day} %H:%M:%S")
            )
            end = start + self.duration
            return start < timestamp < end
        else:
            yesterday = timestamp - timedelta(days=1)
            start = datetime.fromisoformat(
                self.start_time.strftime(f"{yesterday.year}-{yesterday.month}-{yesterday.day} %H:%M:%S")
            )
            end = start + self.duration
            return start < timestamp < end

class DaySchedule:
    def __init__(self, runs):
        self.runs = [SingleRun(**run) for run in runs]
        self.runs.sort(
            key=lambda run: run.start_time
        )

    def check_valid(self,):
        valid = True
        for i in range(len(self.runs)-1):
            run = self.runs[i]
            subsequent_run = self.runs[i+1]
            valid = run.does_not_overlap_with(next=subsequent_run,
                                             same_day=True)
        return valid
    
    def first(self,):
        return self.runs[0]
    
    def last(self,):
        return self.runs[-1]
class WeekSchedule:
    day_types = ('mon', 'tue', 'wed', 'thu',
                 'fri', 'sat', 'sun', 'pub')
    
    def __init__(self, run_schedule): 
        if set(run_schedule.keys()) != set(self.day_types):
            raise Exception('Invalid day type')
        
        self.week_schedule = {
            day_type: DaySchedule(day_schedule)
            for day_type, day_schedule in run_schedule.items()
        }

    def check_all_day_schedule_validity(self,):
        app.logger.debug(f"Checking all day schedule validity")
        day_validity = [
            day_schedule.check_valid()
            for day_schedule in self.week_schedule.values()]
        return all(day_validity)
    
    def check_adjacent_days_validity(self,):
        app.logger.debug(f"Checking adjacent days validity")
        for i in range(7):
            day_type = self.day_types[i]
            subsequent_day_type = self.day_types[(i+1)%7]

            day_last_run = self.week_schedule[day_type].last()
            subsequent_day_first_run = self.week_schedule[subsequent_day_type].first()
            
            valid = day_last_run.does_not_overlap_with(next=subsequent_day_first_run,
                                             same_day=False)
            if not valid:
                return False
            
        return True
    
    def check_week_schedule_validity(self,):
        app.logger.debug(f"Checking week schedule validity")
        all_days = self.check_all_day_schedule_validity()
        adjacent_days = self.check_adjacent_days_validity()
        return all_days and adjacent_days
    
    def get_cron_dow(self, day_type):
        dow_dict = {dow: cron_dow + 1 for cron_dow, dow in enumerate(self.day_types)}
        return dow_dict[day_type]
    
    def check_operational(self, start_timestamp, timezone,
                          is_holiday, is_yesterday_holiday):
        start_timestamp = convert_from_UTC(start_timestamp, timezone)
        today = start_timestamp.strftime("%a").lower()
        yesterday = start_timestamp - timedelta(days=1)
        yesterday = yesterday.strftime("%a").lower()
        if is_holiday:
            dow = 'pub'
        else:
            dow = today
        day_schedule = self.week_schedule[dow]
        for run in day_schedule.runs:
            if run.is_operational_at(start_timestamp, same_day=True):
                return True
            
        if is_yesterday_holiday:
            dow = 'pub'
        else:
            dow = yesterday
        
        day_schedule = self.week_schedule[dow]
        for run in day_schedule.runs:
            if run.is_operational_at(start_timestamp, same_day=False):
                return True
            
        return False
        

class LocationSchedule:
    def __init__(self, location_id, week_schedule, rtsp_infos):
        self.location_id = location_id
        self.week_schedule = week_schedule
        self.rtsp_infos = [RTSPStreamInfo(rtsp_info) for rtsp_info in rtsp_infos]

class EventBridgeSchedulerHandler:
    def __init__(self):
        self.client = scheduler
        self.kvs_handler = KVSHandler()

    def create_location_schedule_group(self, location_id):
        app.logger.info(f"Creating schedule group for location id {location_id}")
        res = self.client.create_schedule_group(
            Name=location_id
        )
        return res.get('ScheduleGroupArn')

    def delete_location_schedule_group(self, location_id):
        app.logger.info(f"Deleting schedule group for location id {location_id}")
        exists, _ = self.check_schedule_exists(location_id)
        if not exists:
            return
        self.client.delete_schedule_group(
            Name=location_id
        )

        app.logger.info(f"Deleting schedule group for location id {location_id} successful")
        app.logger.info(f"Waiting until schedule group for location id {location_id} is completely deleted")
        while exists:
            time.sleep(60)
            exists, _ = self.check_schedule_exists(location_id)
        return

    def check_schedule_group_exists(self, location_id):
        try:
            res = self.client.get_schedule_group(
                Name=location_id
            )
            return True, res
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False, {}
            else:
                raise e
    
    def add_one_schedule(self, location_id, rtsp_info, dow, run):
        app.logger.info(f"Adding schedule of a single run for location id {location_id} and camera id {rtsp_info.camera_id}")

        camera_id = rtsp_info.camera_id
        self.client.create_schedule(
            ScheduleExpression=f"cron({run.start_time.minute} {run.start_time.hour} ? * {dow} * )",
            Name=f"{location_id}-{camera_id}-{dow}-{run.start_time}-{int(time.time())}",
            GroupName=f"{location_id}",
            FlexibleTimeWindow={
                'Mode': 'FLEXIBLE',
                'MaximumWindowInMinutes': 1
            },
            ScheduleExpressionTimezone=rtsp_info.timezone,
            Target={
                'Arn': os.environ['ECS_CLUSTER_ARN'],
                'EcsParameters': {
                    'LaunchType': 'FARGATE',
                    'TaskDefinitionArn': os.environ['ECS_TASK_ARN'],
                    'NetworkConfiguration': {
                        'awsvpcConfiguration': {
                            'Subnets': subnets,
                            'AssignPublicIp': 'ENABLED'
                        }
                    },
                    'Tags': [{
                        'camera_id': camera_id
                    }]
                },
                'RoleArn': os.environ['ECS_ROLE_ARN'],
                'Input': json.dumps({
                    'containerOverrides': [{
                        'name': os.environ['ECS_CONTAINER_NAME'],
                        'environment': [
                            {
                                'name': 'CAMERA_ID',
                                'value': camera_id
                            },
                            {
                                'name': 'STREAM_URL',
                                'value': rtsp_info.stream_url
                            },
                            {
                                'name': 'EXECUTION_TIME',
                                'value': str(run.duration.seconds)
                            },
                            {
                                'name': 'STREAM_NAME',
                                'value': rtsp_info.stream_name
                            },
                            {
                                'name': 'ECS_CLUSTER_ARN',
                                'value': os.environ['ECS_CLUSTER_ARN']
                            },
                            {
                                'name': 'TAG_KEY',
                                'value': 'camera_id'
                            }
                        ]

                    }]
                })
            }
        )

    def add_all_schedule(self, location_schedule):
        app.logger.info(f"Adding all schedules for location id {location_schedule.location_id}")
        for rtsp_info in location_schedule.rtsp_infos:
            app.logger.info(f"Adding schedule for camera id {rtsp_info.camera_id}")
            exists = self.kvs_handler.check_if_stream_exists(rtsp_info.stream_name)
            if not exists:
                app.logger.info(f"KVS stream does not exist. Creating stream for camera id {rtsp_info.camera_id}")
                self.kvs_handler.create_stream(rtsp_info.stream_name, rtsp_info.data_retention)

            for dow, day_schedule in location_schedule.week_schedule.week_schedule.items():
                for run in day_schedule.runs:
                    self.add_one_schedule(location_schedule.location_id,
                                            rtsp_info,
                                            location_schedule.week_schedule.get_cron_dow(dow),
                                            run)

    def update_location_schedule(self, location_schedule):
        self.delete_location_schedule_group(location_schedule.location_id)
        self.create_location_schedule_group(location_schedule.location_id)
        self.add_all_schedule(location_schedule)