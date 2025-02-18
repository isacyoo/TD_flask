import os

from flask import Blueprint, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, func

from clients import s3_client
from utils.auth import error_handler
from utils.metrics import timeit, fail_counter
from databases import db, Video, Camera, Location

video = Blueprint("video", "__name__")
        
@video.get("/video/<id>")
@timeit
@fail_counter
@error_handler()
def get_video(id):
    
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
                                                        'Key':f'videos/{video.id}.mp4'},
                                                ExpiresIn=3600) 
        return jsonify({"url": url})
    except Exception as e:
        app.logger.info(f'Send file failed with {video.id}: {e}')
        return jsonify({"msg": 'Video stream failed'}), 400   

@video.post("/set_video_status/<id>/<status>")
@error_handler(admin=True)
def set_video_status(id, status):
    video = get_video(id)

    if not video:
        app.logger.info(f"Video id {id} not found")
        return jsonify({"msg": "Video not found"}), 404
    
    original_status = video.status
    video.status = status
    db.session.commit()
    return jsonify({"msg": f"Video {id} status updated from {original_status} to {status}"}), 201

@video.get("/check_video_exist/<id>")
@error_handler(admin=True)
def check_video_exist(id):
    video = get_video(id)
    
    if not video:
        return jsonify({"exists": False})
    
    return jsonify({"exists": True})

def get_video(id):
    video = db.session.execute(
        select(Video).where(Video.id==id).limit(1)).scalar_one_or_none()
    return video