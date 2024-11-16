from datetime import timedelta

from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import create_access_token, current_user
from passlib.hash import sha256_crypt
from sqlalchemy import select

from utils.auth import validate_login, admin_required, web_only
from utils.misc import has_all_keys
from databases import db, User

auth = Blueprint("auth", "__name__")

@auth.post("/login")
def create_token() -> Response:
    data = request.get_json()
    if not has_all_keys(data, ["id", "password"]):
        app.logger.info(f'Invalid login credentials provided by {data}')
        return "Invalid login credentials", 401
    id = data["id"]
    password = data["password"]
    verified, user = validate_login(id, password)
    if not verified:
        app.logger.info(f'Invalid login credentials provided by {id}')
        return jsonify({"msg": "Invalid login credentials"}), 401
    token = create_access_token(identity=id, 
                                additional_claims={'is_admin': user.is_admin,
                                                   'is_api': False},)
    response = jsonify({"id":user.id, "name":user.name, "role": 'ADMIN' if user.is_admin else 'USER', "access_token": token})
    app.logger.debug(f'Log in successful for user id {user}')
    return response, 201

@auth.post('/reset_password')
@admin_required
def reset_password() -> Response:
    id = request.json.get("id","")
    user = db.session.execute(
        select(User).where(User.id == id)).scalar_one_or_none()
    
    if not user:
        app.logger.info(f'Password reset request failed due to invalid id: {id}')
        return jsonify({"msg": "Id not found"}), 404
    new_password = request.json.get("password","")
    hash = sha256_crypt.hash(new_password)
    user.password = hash
    db.session.commit()
    app.logger.info(f'Password reset successful for user {id}')
    return jsonify({"msg": "Password reset successful"}), 201

@auth.get("/user_info")
@web_only
def get_user_info() -> Response:
    return jsonify({"id":current_user.id, "name":current_user.name})

@auth.post("/reset_api_key")
@web_only
def reset_api_key():
    token = create_access_token(identity=current_user.id, 
                                additional_claims={'is_admin': current_user.is_admin,
                                                   'is_api': True},
                                expires_delta=timedelta(weeks=52))
    
    current_user.api_key = token
    db.session.commit()
    app.logger.info(f'API_KEY reset successful for user {current_user.id}')
    return jsonify({"msg": "API key reset successful. This API key will be valid for the next 52 weeks.", 
                    "api_key" : token}), 201

@auth.get('/api_key')
@web_only
def get_api_key():
    return jsonify({"api_key" : current_user.api_key})
