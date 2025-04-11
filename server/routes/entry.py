import json
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, Video, Location, Entry, Event
from databases.schemas import EntryWebhookResponseSchema
from utils.auth import error_handler
from utils.upload import *
from utils.hours import convert_to_UTC
from utils.metrics import timeit, fail_counter
from utils.status_codes import EntryStatusCode, VideoStatusCode
from utils.entry import parse_input_data, check_operational


DUPLICATE_THRESHOLD = 5.0
PRECEDE_THRESHOLD = 5.0
VIDEO_LENGTH = 10.0
entry = Blueprint("entry", "__name__")

@entry.post("/entry")
@error_handler(web=False)
@timeit
@fail_counter
def entry_webhook() -> Response:
    data = parse_input_data(request.get_json())

    if not data:
        return jsonify({"msg": "Invalid JSON body"}), 400
    
    location = db.session.execute(
        select(Location).where(Location.id == data["location_id"], Location.user_id == current_user.id)
    ).scalar_one_or_none()
    
    if 'entered_at' in data:
        entered_at = data['entered_at']
        current_time = convert_to_UTC(entered_at, current_user.timezone)
    else:
        current_time = datetime.now(timezone.utc)

    is_operational = check_operational(location, current_time)

    if not is_operational:
        app.logger.info(f"Location {location.name} is not operational")
        return jsonify({"msg": f"Location {location.name} is not operational"}), 200
    
    duplicates = db.session.execute(
        select(Entry).where(
            Entry.member_id==data['member_id'],
            Entry.entered_at<=current_time,
            Entry.entered_at>=current_time-timedelta(seconds=DUPLICATE_THRESHOLD)
        )
    ).first()
    
    if duplicates:
        app.logger.info(f"Duplicate entry detected in {location.name} for {data['member_id']}")
        return jsonify({"msg": "Duplicate entry attempts"}), 201

    event = Event(
        id=str(uuid4()),
        location_id=location.id,
    )

    entry = Entry(
        id=str(uuid4()),
        event_id=event.id,
        member_id=data["member_id"],
        person_meta=json.dumps(data.get("person_meta", {})),
        entered_at=current_time
    )

    db.session.add(event)
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

    if location.upload_method.value == "UserUpload":
        presigned_urls = user_upload(videos)
        app.logger.debug(f"Presigned url issued for {current_user.id} for {entry.id}")

        response = EntryWebhookResponseSchema().dump({
            "entry_id": entry.id,
            "videos": presigned_urls
        })
        
        return jsonify(response), 201
        
    elif location.upload_method.value == "RTSP":
        streams = [camera.stream_url for camera in location.cameras]
        start_timestamps = [current_time + timedelta(seconds=camera.offset_amount) for camera in location.cameras]
        end_timestamps = [start_time + timedelta(seconds=VIDEO_LENGTH) for start_time in start_timestamps]
        
        app.logger.debug(f"RTSP upload started for {entry.id}")

        rtsp_upload(videos, streams, start_timestamps, end_timestamps)

        response = EntryWebhookResponseSchema().dump({
            "entry_id": entry.id,
            "videos": [{"video_id": vid.id} for vid in videos]
        })

        db.session.commit()

        return jsonify(response), 201
    
    elif location.upload_method.value == "Custom":
        pass
    
    else:
        return jsonify({"msg": f"Invalid upload method for location {location.name}"}), 400
        

@entry.post("/set-entry-status/<id>")
@error_handler(admin=True)
def set_entry_status(id):
    all_statuses = [status.name for status in VideoStatusCode]
    data = request.get_json()
    status = data.get("status")
    
    if not status in all_statuses:
        app.logger.info(f"Invalid status {status} provided")
        return jsonify({"msg": f"Invalid status {status} provided"}), 400
    
    entry = db.session.execute(
        select(Entry).where(Entry.id==id)).unique().scalar_one_or_none()

    if not entry:
        app.logger.info(f"Entry id {id} not found")
        return jsonify({"msg": "Entry not found"}), 404
    
    status = EntryStatusCode[status]
    original_status = entry.status
    entry.status = status
    db.session.commit()

    return jsonify({
        "video_id": entry.id,
        "original_status": original_status.name,
        "new_status": status.name
    }), 201