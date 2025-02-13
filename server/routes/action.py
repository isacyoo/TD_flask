import datetime

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, Action, Event
from databases.schemas import ActionSchema
from utils.auth import error_handler

action = Blueprint("action", "__name__")

@action.get("/actions")
@error_handler()
def get_actions() -> Response:
    all_actions = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id)).scalars().all()
    all_actions = ActionSchema(many=True).dump(all_actions)
    
    return jsonify(all_actions)

@action.post("/action")
@error_handler()
def create_action() -> Response:
    data = request.json
    db.session.add(Action(**data))
    db.session.commit()
    return jsonify({"msg": "Add action successful"}), 201

    
@action.post("/action_to_event/<event_id>/<action_id>")
@error_handler()
def apply_action_to_event(event_id, action_id):
    event = db.session.execute(
        select(Event).where(
            Event.id == event_id)).scalars().one_or_none()
    
    if not event:
        app.logger.info(f'Event id {event_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f'Event id {event_id} not found'}), 404
    
    if event.delete_at:
        app.logger.info(f'Event id {event_id} is already deleted | user id: {current_user.id}')
        return jsonify({"msg": f'Event id {event_id} is already deleted'}), 400

    action = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id,
            Action.id == action_id)).scalars().one_or_none()

    if action:
        event.action_id = action_id
        event.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()
        return jsonify({"msg": f"Action {action_id} successfully applied to event {event_id}"}), 201
    else:
        app.logger.info(f'Action id {action_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Action id {action_id} not found"}), 404
