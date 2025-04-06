import datetime

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, update

from databases import db, Action, Event
from databases.schemas import ActionSchema
from utils.auth import error_handler
from utils.action import check_action_exists

action = Blueprint("action", "__name__")

@action.get("/actions")
@error_handler()
def get_actions() -> Response:
    all_actions = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id,
            Action.is_deleted==False)).scalars().all()
    all_actions = ActionSchema(many=True).dump(all_actions)
    
    return jsonify(all_actions)

@action.post("/action")
@error_handler()
def create_action() -> Response:
    data = request.json

    if check_action_exists(data["name"]):
        app.logger.info(f'Action name {data["name"]} already exists | user id: {current_user.id}')
        return jsonify({"msg": "Action name already exists"}), 400
    
    data["user_id"] = current_user.id
    
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
    
    if event.deleted_at:
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

@action.post("/delete_action/<action_id>")
@error_handler()
def delete_action(action_id):
    action = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id,
            Action.id == action_id)).scalars().one_or_none()
    
    if not action:
        app.logger.info(f'Action id {action_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Action id {action_id} not found"}), 404
    
    action_events = db.session.execute(
        select(Event).where(
            Event.action_id == action_id,
            Event.deleted_at.is_(None))).unique().scalars().all()
    
    if action_events:
        app.logger.info(f'Action has associated events | user id: {current_user.id}')
        return jsonify({"msg": f"Action has associated events"}), 400

    action.is_deleted = True
    db.session.commit()
    return jsonify({"msg": f"Action {action_id} deleted"}), 201

@action.post("/update_actions")
@error_handler()
def update_action():
    data = request.json
    for action in data["actions"]:
        if action.get("id") is None:
            if "id" in action:
                del action["id"]
            action["user_id"] = current_user.id
            action = Action(**action)
            db.session.add(action)
        else:
            query = update(Action).where(
                Action.user_id == current_user.id,
                Action.id == action["id"]).values(**action)
            db.session.execute(query)
    db.session.commit()

    return jsonify({"msg": "Update action successful"}), 201