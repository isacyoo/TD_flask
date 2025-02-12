import json
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select
from marshmallow import ValidationError

from databases import db, Video, Camera, RTSPInfo, Location, Entry, Event
from databases.schemas import EntryWebhookInputDataSchema, EntryWebhookResponseSchema
from utils.auth import error_handler
from utils.upload import *
from utils.hours import convert_to_UTC, WeekSchedule
from utils.metrics import timeit, fail_counter
from utils.status_codes import EventStatusCode, VideoStatusCode

PRECEDE_THRESHOLD = 5.0
VIDEO_LENGTH = 10.0
entry = Blueprint("entry", "__name__")

def parse_input_data(data):
    try:
        result = EntryWebhookInputDataSchema().load(data)
        return result
    except ValidationError as e:
        app.logger.info(f"Error parsing JSON data: {e}")
        return None
    
def check_operational(location, current_time):
    operational_hours = location.operational_hours

    if not operational_hours:
        app.logger.info(f"Operational hours not found for location {location.name}")
        return False
        
    week_schedule = WeekSchedule(json.loads(operational_hours))
    is_operational = week_schedule.check_operational(current_time, current_user.timezone, False, False)

    return is_operational

@entry.post("/entry")
@timeit
@fail_counter
@error_handler(web=False)
def entry_webhook() -> Response:
    try:
        data = parse_input_data(request.get_json())

        if not data:
            return jsonify({"msg": "Invalid JSON body"}), 400
        
        location = data["location"]
        
        if 'entered_at' in data:
            entered_at = datetime(data['entered_at'])
            current_time = convert_to_UTC(entered_at, current_user.timezone)
        else:
            current_time = datetime.now(timezone.utc)

        is_operational = check_operational(location, current_time)

        if not is_operational:
            app.logger.info(f"Location {location.name} is not operational")
            return jsonify({"msg": f"Location {location.name} is not operational"}), 200
        
        duplicates = db.session.execute(
            select(Entry).where(
                Entry.person_id==data['person_id'],
                Entry.entered_at==current_time,
                Entry.entry_id==data['entry_id']
            )
        ).first()
        
        if duplicates:
            app.logger.info(f"Duplicate entry detected in {location.name} for {data['person_id']}")
            return jsonify({"msg": "Duplicate entry attempts"}), 201

        entry = Entry(
            id=str(uuid4()),
            event_id=None,
            person_id=data["person_id"],
            person_meta=json.dumps(data.get("person_meta", {})),
            entered_at=current_time
        )

        db.session.add(entry)

        videos = []

        for camera in location.cameras:
            vid = Video(
                id=str(uuid4()),
                camera_id=camera.id,
                entry_id=entry.id,
                status=VideoStatusCode.CREATED
            )

            db.session.add(vid)
            videos.append(vid)

        db.session.commit()
        if location.upload_method == "UserUpload":
            presigned_urls = user_upload(videos)
            app.logger.debug(f"Presigned url issued for {current_user.id} for {entry.id}")

            response = EntryWebhookResponseSchema().dump({
                "entry_id": entry.id,
                "videos": presigned_urls
            })
            
            return jsonify(response), 201
            
        elif location.upload_method == "RTSP":
            rtsp_info = db.session.execute(
                select(RTSPInfo).where(RTSPInfo.camera_id.in_([camera.id for camera in location.cameras]))).scalars().all()
            
            streams = [info.stream_url for info in rtsp_info]
            start_timestamps = [current_time + timedelta(seconds=info.offset_amount) for info in rtsp_info]
            end_timestamps = [start_time + timedelta(seconds=VIDEO_LENGTH) for start_time in start_timestamps]

            app.logger.debug(f"RTSP upload started for {entry.id}")

            rtsp_upload(videos, streams, start_timestamps, end_timestamps)

            response = EntryWebhookResponseSchema().dump({
                "entry_id": entry.id,
                "videos": [{"video_id": vid.id} for vid in videos]
            })

            return jsonify(response), 201
        
        elif location.upload_method == "Custom":
            pass
        
        else:
            return jsonify({"msg": f"Invalid upload method for location {location.name}"}), 400

    except Exception as e:
        app.logger.info(f'Upload failed with provided data {request.get_json()}: {e}')
        return jsonify({"msg": "Upload failed"}), 400
        