import os

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, func
from werkzeug.exceptions import NotFound

from clients import s3_client
from utils.auth import error_handler
from utils.metrics import timeit, fail_counter
from databases import db, Video, Location, query_videos, get_page_info
from databases.schemas import EventSchema

video = Blueprint("video", "__name__")
BUCKET_NAME = "td.bucket"
PER_PAGE = 1

def parse_time_range(time_range):
    if not time_range:
        return None
    unit = time_range[-1]
    if unit == 'h':
        return int(time_range[:-1])*60*60
    elif unit == 'd':
        return int(time_range[:-1])*60*60*24
    elif unit == 'w':
        return int(time_range[:-1])*60*60*24*7
    
    return None

@video.get("/all_unreviewed_events/<location_id>")
@error_handler()
def get_all_unreviewed_events(location_id) -> Response:
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_videos(location_id, person_id, time_range, None)
        
    events = db.session.execute(query).scalars().all()
    events = EventSchema(many=True).dump(events)

    return jsonify(events)

@video.get("/unreviewed_events/<location_id>/<int:page>")
@timeit
@error_handler()
def get_unreviewed_events(location_id, page) -> Response:
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_videos(location_id, person_id, time_range, None)
    
    try:
        unreviewed_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = EventSchema(many=True).dump(unreviewed_paginate.items)
    page_info = get_page_info(unreviewed_paginate)
    res = {"events": events} | page_info

    return jsonify(res)

@video.get("/all_history_events/<location_id>")
@error_handler()
def get_all_history_events(location_id) -> Response:
    action_ids = request.args.getlist("actionId", None)
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_videos(location_id, person_id, time_range, action_ids, True)
    
    events = db.session.execute(query).scalars().all()
    events = EventSchema(many=True).dump(events)
    
    return jsonify(events)

@video.get("/history_events/<location_id>/<int:page>")
@timeit
@error_handler()
def get_history_events(location_id, page) -> Response:
    action_ids = request.args.getlist("actionId", None)
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_videos(location_id, person_id, time_range, action_ids, True)
    try:
        history_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = EventSchema(many=True).dump(history_paginate.items)
    page_info = get_page_info(history_paginate)
    res = {"events": events} | page_info

    return jsonify(res)
        
    
@video.get("/adjacent_videos/<id>")
@error_handler(api=False)
def get_adjacent_videos(id):
    action_id = request.args.get("actionId", None)
    person_id = request.args.get("personId", None)
    current_video = db.session.execute(
        select(Video).where(
            Video.user_id==current_user.id, 
            Video.id==id)).scalar_one_or_none()

    if not current_video:
        app.logger.info(f'Adjacent video could not be found as the video does not exist: {current_user.id} - {id}')
        return jsonify({"msg": "Video not found"}), 404
    if not current_video.status in (REVIEW_DONE, REVIEW_READY):
        app.logger.info(f'Adjacent video could not be found as the video is not primary: {current_user.id} - {id}')
        return jsonify({"msg": "Video not primary"}), 400
    
    next_query = select(Video.id)
    
    next_query = next_query.where(
        Video.user_id==current_user.id, 
        Video.entered_at<current_video.entered_at,
        Video.status==current_video.status,
        Video.camera_id==current_video.camera_id
        )
    
    if action_id:
        next_query = next_query.where(Video.action_id==action_id)
    if person_id:
        next_query = next_query.where(Video.person_id==person_id)
    next_query = next_query.order_by(
        Video.entered_at.desc(), Video.id.desc()
    )
    next_query = next_query.limit(1)
    
    previous_query = select(Video.id)
    
    previous_query = previous_query.where(
        Video.user_id==current_user.id, 
        Video.entered_at>current_video.entered_at,
        Video.status==current_video.status,
        Video.camera_id==current_video.camera_id
        )
    
    if action_id:
        previous_query = previous_query.where(Video.action_id==action_id)
    if person_id:
        previous_query = previous_query.where(Video.person_id==person_id)
        
    previous_query = previous_query.order_by(
        Video.entered_at, Video.id
    )
    previous_query = previous_query.limit(1)
    
    next_video = db.session.execute(next_query).first()
    previous_video = db.session.execute(previous_query).first()
            
    if next_video:
        app.logger.debug(f'Next video of video {id} found - {next_video.id}')
        next_video = next_video.id
    
    if previous_video:
        app.logger.debug(f'Previous video of video {id} found - {previous_video.id}')
        previous_video = previous_video.id
        
    return jsonify({"next_video": next_video, "previous_video": previous_video})
        
@video.get("/video/<id>")
@timeit
@fail_counter
@error_handler()
def get_video(id):
    video = db.session.execute(
        select(Video).where(
            Video.user_id==current_user.id, 
            Video.id==id)).scalar_one_or_none()

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

@video.get("/check_video_primary/<id>")
@error_handler(admin=True)
def check_video_primary(id):
    video = get_video(id)
    if not video:
        return jsonify({"msg": "Video not found"}), 404
    return jsonify({"is_primary": video_is_primary(video)})
  
@video.get("/total_unreviewed_videos")
@error_handler()
def get_total_unreviewed_videos():
    query = select(func.count()).select_from(Video).where(
        Video.user_id==current_user.id,
        Video.status==REVIEW_READY)
    res = db.session.execute(query).scalar()
    return jsonify({"total_unreviewed": res})

@video.get("/total_unreviewed_videos_per_location")
@error_handler()
def get_total_unreviewed_videos_per_location():
    query = select(Location.id, Location.name, func.count()).select_from(Video)
    query = join_camera(query)
    query = join_location(query)
    query = query.where(
        Video.user_id==current_user.id,
        Video.status==REVIEW_READY).group_by(
            Location.id)
    res = db.session.execute(query).all()
    keys = ['id', 'name', 'count']
    return serialize(res, keys)

def get_video(id):
    video = db.session.execute(
        select(Video).where(Video.id==id).limit(1)).scalar_one_or_none()
    return video