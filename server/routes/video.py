import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask import current_app as app, request
from flask_jwt_extended import current_user
from sqlalchemy import select

from clients import s3_client
from utils.auth import error_handler
from utils.metrics import timeit, fail_counter
from utils.video import get_video, send_video_to_queue
from utils.status_codes import VideoStatusCode, EntryStatusCode
from databases import db, Video, Camera, Location

video = Blueprint("video", "__name__")
        
@video.get("/video/<id>")
@timeit
@fail_counter
@error_handler()
def generate_video_url(id):
    video = db.session.execute(
        select(Video).join(Camera).join(Location).where(
            Location.user_id==current_user.id, 
            Video.id==id)).unique().scalar_one_or_none()

    if not video:
        app.logger.info(f'Video id {id} not found | user id: {current_user.id}')
        return jsonify({"msg": "Video not found"}), 404
    try:
        url = s3_client.generate_presigned_url('get_object',
                                                Params={'Bucket':os.getenv('S3_BUCKET_NAME'),
                                                        'Key':f'resized/hd/{video.id}.mp4'},
                                                ExpiresIn=3600) 
        return jsonify({"url": url})
    except Exception as e:
        app.logger.info(f'Send file failed with {video.id}: {e}')
        return jsonify({"msg": 'Video stream failed'}), 400

@video.put("/video-status/<id>")
@error_handler(admin=True)
def set_video_status(id):
    all_statuses = [status.name for status in VideoStatusCode]
    data = request.get_json()
    status = data.get("status")
    
    if not status in all_statuses:
        app.logger.info(f"Invalid status {status} provided")
        return jsonify({"msg": f"Invalid status {status} provided"}), 400
    
    video = get_video(id)

    if not video:
        app.logger.info(f"Video id {id} not found")
        return jsonify({"msg": "Video not found"}), 404
    
    status = VideoStatusCode[status]
    original_status = video.status
    video.status = status

    if status == VideoStatusCode.PROCESS_READY:
        video.uploaded_at = datetime.now(timezone.utc)
    
    db.session.commit()

    return jsonify({
        "video_id": video.id,
        "original_status": original_status.name,
        "new_status": status.name
    }), 201

@video.post('/confirm-upload/<id>')
@error_handler(admin=True)
def confirm_upload(id):
    video = get_video(id)

    if not video:
        app.logger.info(f"Video id {id} not found")
        return jsonify({"msg": "Video not found"}), 404

    video.status = VideoStatusCode.PROCESS_READY
    video.uploaded_at = datetime.now(timezone.utc)

    other_videos = db.session.execute(
        select(Video).where(
            Video.entry_id==video.entry_id,
            Video.id!=id,
            Video.status!=VideoStatusCode.PROCESS_READY)).unique().scalars().all()
    
    if not other_videos:
        video.entry.status = EntryStatusCode.PROCESS_READY
    
    db.session.commit()

    camera = db.session.execute(
        select(Camera).where(Camera.id==video.camera_id)).scalar_one_or_none()
    send_video_to_queue(video, camera)

    return jsonify({"msg": "Upload success"}), 201

@video.get("/video-existence/<id>")
@error_handler(admin=True)
def check_video_exist(id):
    video = db.session.execute(
        select(Video).where(Video.id==id)).unique().scalar_one_or_none()
    
    if not video:
        return jsonify({"exists": False})
    
    return jsonify({"exists": True})