import json
from uuid import uuid4
from datetime import datetime, timedelta

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, Video, Camera, RTSPInfo
from server.routes.location import grab_location_id
from utils.auth import error_handler
from utils.misc import has_all_keys
from utils.upload import *
from utils.hours import convert_to_UTC, WeekSchedule
from utils.metrics import timeit, fail_counter
from constants import CREATION_READY, UPLOAD_IN_PROGRESS

CHILD_THRESHOLD = 5.0
VIDEO_LENGTH = 10.0
upload = Blueprint("upload", "__name__")
@upload.post("/upload")
@timeit
@fail_counter
@error_handler(web=False)
def upload_videos() -> Response:
    try:
        data = request.get_json()
        required_keys = ["id", "api_key","location_name", "camera_name", "entry_id", "person_id"]
        if not has_all_keys(data, required_keys):
            app.logger.info(f"JSON body does not have all the required keys: {data}")
            return jsonify({"msg": f"JSON body does not have all the required keys: {required_keys}"}), 400
            
        location = grab_location_id(current_user.id, data["location_name"])
        if not location:
            return jsonify({"msg": f"Location name {data['location_name']} is not valid"}), 400
        
        all_cameras = db.session.execute(
            select(Camera).where(Camera.location_id==location.id)).scalars().all()
        
        if not all_cameras:
            return jsonify({"msg": f"Camera not found for location {data['location_name']}"}), 404
        
        if 'entered_at' in data:
            entered_at = datetime.datetime(data['entered_at'])
            current_time = convert_to_UTC(entered_at, current_user.timezone)
        else:
            current_time = datetime.utcnow()

        operational_hours = location.operational_hours
        if not operational_hours:
            app.logger.info(f"Operational hours not found for location {location.name}")
            return jsonify({"msg": f"Operational hours not found for location {location.name}"}), 404
        
        week_schedule = WeekSchedule(json.loads(operational_hours))
        is_operational = week_schedule.check_if_operational(current_time)
        
        if not is_operational:
            app.logger.info(f"Location {location.name} is not operational at {current_time}")
            return jsonify({"msg": f"Location {location.name} is not operational at {current_time}"}), 400
        duplicates = db.session.execute(
            select(Video.id).where(
                Video.person_id==data['person_id'],
                Video.entered_at==current_time,
                Video.entry_id==data['entry_id']
            )).first()
        
        if duplicates:
            app.logger.info(f"Duplicate entry detected in {location.name} for {data['person_id']}")
            return jsonify({"msg": "Duplicate entry attempts"}), 400
        
        video_ids = [str(uuid4) for _ in len(all_cameras)]
        for camera, video_id in zip(all_cameras, video_ids):
            video_id = str(uuid4())
            vid = Video(id=video_id, user_id=current_user.id, camera_id=camera.id,
                        entry_id=data["entry_id"], person_id=data["person_id"],
                        person_meta=data.get("person_meta", "{}"), status=CREATION_READY,
                        entered_at=current_time)
            db.session.add(vid)
        db.session.commit()
        if location.upload_method == "UserUpload":
            response = user_upload(video_ids, all_cameras)
            app.logger.debug(f"Presigned url issued for {current_user.id} for {video_ids}")
            return jsonify(response), 201    
            
        elif location.upload_method == "RTSP":
            rtsp_info = db.session.execute(
                select(RTSPInfo).where(RTSPInfo.camera_id.in_([camera.id for camera in all_cameras]))).scalars().all()
            streams = [info.stream_url for info in rtsp_info]
            start_timestamps = [current_time + timedelta(seconds=info.offset_amount) for info in rtsp_info]
            end_timestamps = [start_time + timedelta(seconds=VIDEO_LENGTH) for start_time in start_timestamps]
            app.logger.debug(f"RTSP upload started for {video_ids}")
            rtsp_upload(video_ids, streams, start_timestamps, end_timestamps)
            return jsonify({"msg": "Upload in progress"}), 201
        
        elif location.upload_method == "Custom":
            pass
        
        else:
            return jsonify({"msg": f"Invalid upload method for location {location.name}"}), 400

    except Exception as e:
        app.logger.info(f'Upload failed with provided data {request.get_json()}: {e}')
        return jsonify({"msg": "Upload failed"}), 400
        
@upload.post("/confirm_upload/<video_id>")
@error_handler(admin=True)
def confirm_upload(video_id):
    video = db.session.execute(
        select(Video).where(Video.id==video_id)).scalar()
    
    if not video:
        return jsonify({"msg": f"Video {video_id} does not exist in the database"}), 404
    
    video.status = UPLOAD_IN_PROGRESS
    video.uploaded_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({"msg": "Upload confirmed"}), 201
    
    
@upload.post("/find_parent/<video_id>")
@error_handler(admin=True)
def find_parent(video_id):
    video, camera = db.session.execute(
        select(Video, Camera).join(
            Camera, Camera.id==Video.camera_id
        ).where(
            Video.id==video_id
        ).limit(1)).first()
    
    if not camera.is_primary:
        app.logger.debug(f"Video {video_id} is not from a primary camera")
        return jsonify({"is_primary": False}), 200
    
    lower_bound = video.entered_at - timedelta(seconds=CHILD_THRESHOLD)
    parent_entry_id = db.session.execute(
        select(Video.entry_id).where(
            Video.camera_id == video.camera_id,
            Video.entered_at < video.entered_at,
            Video.entered_at > lower_bound,
            Video.person_id != video.person_id
        ).order_by(Video.entered_at.desc()).limit(1)).scalar_one_or_none()
    
    if not parent_entry_id:
        app.logger.debug(f"Parent not found for video {video_id}")
        return jsonify({"is_primary": True}), 200
    else:
        # parent_child = ParentChildDetected(parent=parent_entry_id,
        #                                    child=video.entry_id)
        db.session.add(parent_child)
        db.session.commit()
        app.logger.debug(f"Parent entry id {parent_entry_id} found for video {video_id}")
        return jsonify({"is_primary": False}), 200
        