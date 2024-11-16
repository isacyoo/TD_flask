import os
import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, func

from clients import s3_client
from utils.auth import admin_required, web_only, both_web_and_api
from utils.metrics import timeit, fail_counter
from constants import REVIEW_DONE, REVIEW_READY
from databases import *

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

def video_is_primary(video):
    camera = db.session.execute(
        select(Camera).where(Camera.id==video.camera_id)).scalar()
    parent = db.session.execute(
        select(ParentChildDetected).where(ParentChildDetected.child==video.entry_id)).scalar()
    if not parent and camera.is_primary:
        return True
    
    return False

@video.get("/all_unreviewed_videos/<location_id>")
@both_web_and_api
def get_all_unreviewed_videos(location_id) -> Response:
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = select(Video.id,
                   Video.person_id,
                   Video.entry_id,
                   Video.entered_at,
                   Location.name)
    query = query_unreviewed_videos(query, location_id)
    query = join_location(query)
    if person_id:
        query = query.where(Video.person_id==person_id)
    if time_range:
        start_time = datetime.now(timezone.utc) - timedelta(seconds=int(time_range))
        query = query.where(Video.entered_at>start_time)
        
    query = query.order_by(
        Video.entered_at.desc(), Video.id.desc())
        
    videos = db.session.execute(query).all()
    keys = ["id", "person_id", "entry_id", "entered_at"]
    res = [{ key:check_type_and_format(getattr(video, key)) for key in keys} |
           {"location": video.name} for video in videos]
    return jsonify(res)

@video.get("/unreviewed_videos/<location_id>/<int:page>")
@timeit
@both_web_and_api
def get_unreviewed_videos(location_id, page) -> Response:
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))
    
    query = select(Video.id,
                   Video.person_id,
                   Video.entry_id,
                   Video.entered_at,)
    query = query_unreviewed_videos(query, location_id)

    if person_id:
        query = query.where(Video.person_id==person_id)
    if time_range:
        start_time = datetime.now(timezone.utc) - timedelta(seconds=int(time_range))
        query = query.where(Video.entered_at>start_time)
        
    query = query.order_by(
        Video.entered_at.desc(), Video.id.desc())
    unreviewed_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    
    video_keys = ["id","person_id","entry_id", "entered_at"]
    page_keys = ["pages", "per_page", "total"]
    iter_pages = unreviewed_paginate.iter_pages(left_current=3,
                                             right_current=3)
    videos = [{key: check_type_and_format(
        getattr(video, key)) for key in video_keys} for video in unreviewed_paginate.items]
    page_info = {key: getattr(unreviewed_paginate, key)
                 for key in page_keys} | {"iter_pages": list(iter_pages)}
    res = {"videos": videos} | page_info
    return jsonify(res)

@video.get("/all_history_videos/<location_id>")
@both_web_and_api
def get_all_history_videos(location_id) -> Response:
    action_ids = request.args.getlist("actionId", None)
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))
    
    query = select(Video.id,
                   Video.person_id,
                   Video.entry_id,
                   Video.entered_at,
                   Action.name)
    query = query_history_videos(query, location_id)
    
    if action_ids:
        query = query.where(Video.action_id.in_(action_ids))
    if person_id:
        query = query.where(Video.person_id==person_id)
    if time_range:
        start_time = datetime.now(timezone.utc) - timedelta(seconds=int(time_range))
        query = query.where(Video.entered_at>start_time)
        
    query = query.order_by(
        Video.entered_at.desc(), Video.id.desc())
    
    videos = db.session.execute(query).all()
    video_keys = ["id", "person_id", "entry_id", "entered_at"]
    
    res = [{ key:check_type_and_format(getattr(video, key)) for key in video_keys} |
                {"action": video.name} for video in videos]
    
    return jsonify(res)

@video.get("/history_videos/<location_id>/<int:page>")
@timeit
@both_web_and_api
def get_history_videos(location_id, page) -> Response:
    action_ids = request.args.getlist("actionId", None)
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))
    
    query = select(Video.id,
                   Video.person_id,
                   Video.entry_id,
                   Video.entered_at,
                   Action.name)
    query = query_history_videos(query, location_id)
    
    if action_ids:
        query = query.where(Video.action_id.in_(action_ids))
    if person_id:
        query = query.where(Video.person_id==person_id)
    if time_range:
        start_time = datetime.now(timezone.utc) - timedelta(seconds=int(time_range))
        query = query.where(Video.entered_at>start_time)
        
    query = query.order_by(
        Video.entered_at.desc(), Video.id.desc())
    
    history_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    
    video_keys = ["id", "person_id", "entry_id", "entered_at"]
    page_keys = ["pages", "per_page", "total"]
    iter_pages = history_paginate.iter_pages(left_current=3,
                                             right_current=3)
    
    videos = [{ key: check_type_and_format(getattr(video, key)) for key in video_keys} |
        {"action": video.name} for video in history_paginate.items]
    page_info = { key: getattr(history_paginate, key) for key in page_keys} | {"iter_pages": list(iter_pages)}
    res = {"videos": videos} | page_info
    return jsonify(res)

@video.get("/all_videos_with_first_entry_video_id/<id>")
@both_web_and_api
def get_all_videos_with_first_entry(id):
    primary_video = select(
        Video.id,
        Video.camera_id,
        Video.entry_id,
        Video.action_id,
        Video.status,
        Action.name,
        Location.id.label("location_id"),
    )
    primary_video = join_action(primary_video, is_outer=True)
    primary_video = join_camera(primary_video)
    primary_video = join_location(primary_video)
    primary_video = with_user_identity(primary_video)
    primary_video = primary_video.where(
        Video.id == id)
    primary_video = primary_video.limit(1)
    primary_video = db.session.execute(primary_video).first()

    if not primary_video:
        return {"msg": "Video not found"}, 404
    if not video_is_primary(primary_video):
        return jsonify({"msg": "Video not primary"}), 400
    
    videos = []
    def find_child_videos(parent):   
        query = select(Video.id,
                    Video.person_id,
                    Video.entry_id,
                    Video.status,
                    Video.entered_at,
                    Video.person_meta,
                    Location.name.label("location_name"),
                    ParentChildDetected.child)
        query = join_camera(query)
        query = join_location(query)
        query = join_parent_child_detected(query, join_child=False)
        query = with_user_identity(query)
        query = query.where(
            Video.entry_id == parent)
        query = query.order_by(
            Camera.is_primary.desc())
        return list(db.session.execute(query).all())
    
    children_found = find_child_videos(primary_video.entry_id)
        
    while children_found:
        videos += children_found
        child_entry_id = children_found[0].child
        if not child_entry_id:
            break
        children_found = find_child_videos(child_entry_id)
        
    keys = ["id", "person_id", "entry_id", "status", "entered_at"]
    videos = [
        { key: check_type_and_format(getattr(video, key)) for key in keys} |
        {"location": video.location_name, "person_meta": json.loads(video.person_meta)} for video in videos
    ]
    res = {
        'action': {
            'id': primary_video.action_id,
            'name': primary_video.name
            },
        'videos': videos,
        'location': primary_video.location_id,
        'history': primary_video.status == REVIEW_DONE
    }
    return jsonify(res)
        
    
@video.get("/adjacent_videos/<id>")
@web_only
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
@both_web_and_api
def get_video(id):
    video = db.session.execute(
        select(Video).where(
            Video.user_id==current_user.id, 
            Video.id==id)).scalar_one_or_none()

    if not video:
        app.logger.info(f'Video id {id} not found | user id: {current_user.id}')
        return jsonify({"msg": "Video not found"}), 404
    try:
        url = s3_client.generate_presigned_url(
                                                'get_object',
                                                Params={'Bucket':os.getenv('S3_BUCKET_NAME'),
                                                        'Key':f'videos/{video.id}.mp4'},
                                                ExpiresIn=3600) 
        return {"url": url}
    except Exception as e:
        app.logger.info(f'Send file failed with {video.id}: {e}')
        return jsonify({"msg": 'Video stream failed'}), 400   

@video.post("/set_video_status/<id>/<status>")
@admin_required
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
@admin_required
def check_video_exist(id):
    video = get_video(id)
    if not video:
        return jsonify({"exists": False})
    return jsonify({"exists": True})

@video.get("/check_video_primary/<id>")
@admin_required
def check_video_primary(id):
    video = get_video(id)
    if not video:
        return jsonify({"msg": "Video not found"}), 404
    return jsonify({"is_primary": video_is_primary(video)})
  
@video.get("/total_unreviewed_videos")
@both_web_and_api
def get_total_unreviewed_videos():
    query = select(func.count()).select_from(Video).where(
        Video.user_id==current_user.id,
        Video.status==REVIEW_READY)
    res = db.session.execute(query).scalar()
    return jsonify({"total_unreviewed": res})

@video.get("/total_unreviewed_videos_per_location")
@both_web_and_api
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