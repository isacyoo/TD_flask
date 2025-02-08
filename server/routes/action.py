import datetime

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from constants import REVIEW_DONE, REVIEW_READY
from databases import db, Action, Video
from utils.auth import error_handler

action = Blueprint("action", "__name__")

CAN_APPLY_ACTION_STATUS = [REVIEW_READY, REVIEW_DONE]

@action.get("/actions")
@error_handler()
def get_actions() -> Response:
    all_actions = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id)).scalars().all()
    all_actions = [{"id": action.id, "name": action.name, "deleted": action.is_deleted} for action in all_actions]
    return jsonify(all_actions)

@action.post("/action")
@error_handler()
def create_action() -> Response:
    data = request.json
    db.session.add(Action(**data))
    db.session.commit()
    return jsonify({"msg": "Add action successful"}), 201

    
@action.post("/action_to_video/<video_id>/<action_id>")
@error_handler()
def apply_action_to_video(video_id, action_id):
    video = db.session.execute(
        select(Video).where(
            Video.user_id == current_user.id,
            Video.id == video_id)).scalars().one_or_none()
        
    if not video:
        app.logger.info(f'Video id {video_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f'Video id {video_id} not found'}), 404
    
    if video.status not in CAN_APPLY_ACTION_STATUS:
        app.logger.info(f'Video id {video_id} has status {video.status} | user id: {current_user.id}')
        return jsonify({"msg": f'Video does not have the right status code to perform this action'}), 400
    action = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id,
            Action.id == action_id)).scalars().one_or_none()

    if action:
        video.action_id = action_id
        video.status = REVIEW_DONE
        video.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()
        return jsonify({"msg": f"Action {action_id} successfully applied to video {video_id}"}), 201
    else:
        app.logger.info(f'Action id {action_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Action id {action_id} not found"}), 404
