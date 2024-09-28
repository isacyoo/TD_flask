from datetime import datetime

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from constants import REVIEW_DONE, REVIEW_READY
from databases import db, Action, Video
from utils.auth import both_web_and_api

action = Blueprint("action", "__name__")

CAN_APPLY_ACTION_STATUS = [REVIEW_READY, REVIEW_DONE]

@action.get("/actions")
@both_web_and_api
def get_actions() -> Response:
    all_actions = Action.query.filter_by(user_id=current_user.id).all()
    all_actions = {action.name: {'id': action.id, 'deleted': action.is_deleted} for action in all_actions}
    return jsonify(all_actions)

@action.post("/action")
@both_web_and_api
def create_action() -> Response:
    data = request.get_json()
    db.session.add(Action(**data))
    db.session.commit()
    return jsonify({"msg": "Add action successful"}), 201

    
@action.post("/action_to_video/<video_id>/<action_id>")
@both_web_and_api
def apply_action_to_video(video_id, action_id):
    video = db.session.execute(
        select(Video).filter_by(user_id=current_user.id, id=video_id).limit(1)).scalar_one_or_none()
    
    if not video:
        app.logger.info(f'Video id {video_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f'Video id {video_id} not found'}), 404
    
    if video.status not in CAN_APPLY_ACTION_STATUS:
        app.logger.info(f'Video id {video_id} has status {video.status} | user id: {current_user.id}')
        return jsonify({"msg": f'Video does not have the right status code to perform this action'}), 400
    
    action = db.session.execute(
        select(Action).filter_by(user_id=current_user.id, id=action_id).limit(1)).scalar_one_or_none()
    
    if action:
        video.action_id = action_id
        video.status = REVIEW_DONE
        video.reviewed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"msg": f"Action {action_id} successfully applied to video {video_id}"}), 201
    else:
        app.logger.info(f'Action id {action_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Action id {action_id} not found"}), 404
