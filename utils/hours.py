from datetime import time, timedelta, datetime
from zoneinfo import ZoneInfo

from flask import current_app as app

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
        if self.runs:
            return self.runs[0]
        return None
    
    def last(self,):
        if self.runs:
            return self.runs[-1]
        return None
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
            
            if day_last_run is None or subsequent_day_first_run is None:
                continue
            
            valid = day_last_run.does_not_overlap_with(next=subsequent_day_first_run,
                                             same_day=False)
            if not valid:
                return False
            
        return True
    
    def check_week_schedule_validity(self,):
        app.logger.debug(f"Checking week schedule validity")
        all_days = self.check_all_day_schedule_validity()
        adjacent_days = self.check_adjacent_days_validity()
        app.logger.debug("All day schedule validity: %s", all_days)
        app.logger.debug("Adjacent day schedule validity: %s", adjacent_days)
        
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