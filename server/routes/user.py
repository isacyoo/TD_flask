from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from sqlalchemy import select
from flask_jwt_extended import current_user

from utils.auth import error_handler
from databases import db, User
from databases.schemas import UserSettingSchema, UpdateUserSettingInputSchema

users = Blueprint("users", "__name__")

@users.post("/user")
@error_handler(admin=True)
def create_user() -> Response:
    data = request.get_json()
    db.session.add(User(**data))
    db.session.commit()
    return jsonify({"msg": f"Successfully created user {data['id']}"}), 201

@users.get("/user-settings")
@error_handler()
def get_user_settings() -> Response:
    user_id = current_user.id
    user = db.session.execute(
        select(User).where(
            User.id == user_id)).scalars().one_or_none()
    
    if not user:
        app.logger.info(f'User id {user_id} not found')
        return jsonify({"msg": f'User id {user_id} not found'}), 404
    
    return jsonify(UserSettingSchema().dump(user)), 200

@users.put("/user-settings")
@error_handler()
def update_user_settings() -> Response:
    user_id = current_user.id
    data = UpdateUserSettingInputSchema().load(request.get_json())
    user = db.session.execute(
        select(User).where(
            User.id == user_id)).scalars().one_or_none()
    
    if not user:
        app.logger.info(f'User id {user_id} not found')
        return jsonify({"msg": f'User id {user_id} not found'}), 404
    
    for key, value in data.items():
        setattr(user, key, value)
    
    db.session.commit()
    app.logger.info(f'User id {user_id} settings updated')

    res = UserSettingSchema().dump(user)
    return jsonify(res), 200