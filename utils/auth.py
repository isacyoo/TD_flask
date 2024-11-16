from functools import wraps
from re import split
import traceback

from passlib.hash import sha256_crypt
from flask import current_app as app, jsonify
from flask import request
from flask_jwt_extended import get_jwt, verify_jwt_in_request, current_user
from sqlalchemy import select

from databases import User, db

def get_raw_jwt():
    auth_header = request.headers.get('Authorization', None)
    field_values = split(r",\s*", auth_header)
    jwt_headers = [s for s in field_values if s.startswith("Bearer")]
    
    parts = jwt_headers[0].split()
    return parts[1] 
    
def validate_login(id, password):
    user = db.session.execute(
        select(User).where(User.id == id)).scalar_one_or_none()
    if not user:
        return False, None
    verified = sha256_crypt.verify(password, user.password)
    
    return verified, user

def error_handler(web=False, api=False, admin=False):
    def inner(fn):
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if web and not api:
                if claims.get("is_api"):
                    app.logger.warning('This endpoint is not intended for API use')
                    return jsonify({"msg": "This endpoint is not intended for API use"}), 403
            if api and not web:
                if not claims.get("is_api"):
                    app.logger.warning('This endpoint is not intended for web use')
                    return jsonify({"msg": "This endpoint is not intended for web use"}), 403
            if admin:
                if not claims["is_admin"]:
                    app.logger.warning('Unauthorized user attempted an admin-only API')
                    return jsonify({"msg": "Unauthorized"}), 401
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                app.logger.warning(f'User id: {current_user.id} || location: {fn} || error {traceback.format_exc()}')
                return jsonify({"msg": "Method unsuccessful"}), 400
            
        return wrapper
    return inner            

def admin_required(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims["is_admin"]:
            if claims["is_api"]:
                raw_jwt = get_raw_jwt()
                if raw_jwt != current_user.api_key:
                    app.logger.warning(f'API key does not match user id {current_user.id}')
                    return jsonify({"msg": "API key does not match user id"}), 401
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                app.logger.error(f'User id: {current_user.id} || location: {fn} || error {e}')
                return jsonify({"msg": "Method unsuccessful"}), 400
        else:
            app.logger.warning('Unauthorized user attempted an admin-only API')
            return jsonify({"msg": "Unauthorized"}), 401

    return decorator

def api_only(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if not claims.get("is_api"):
            app.logger.warning(f'Unauthorized user {current_user.id} attempted an API that is only available through API key')
            return jsonify({"msg": "Unauthorized"}), 401
            
        raw_token = get_raw_jwt()
        if raw_token != current_user.api_key:
            app.logger.warning(f'API key does not match user id {current_user.id}')
            return jsonify({"msg": "API key does not match user id"}), 401
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            app.logger.error(f'User id: {current_user.id} || location: {fn} || error {e}')
            return jsonify({"msg": "Method unsuccessful"}), 400

    return decorator

def web_only(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("is_api"):
            app.logger.warning('This endpoint is not intended for API use')
            return jsonify({"msg": "This endpoint is not intended for API use"}), 403
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            app.logger.error(f'User id: {current_user.id} || location: {fn} || error" {e}')
            return jsonify({"msg": "Method unsuccessful"}), 400

    return decorator

def both_web_and_api(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("is_api"):
            raw_token = get_raw_jwt()
            if raw_token != current_user.api_key:
                app.logger.warning(f'API key does not match user id {current_user.id}')
                return jsonify({"msg": "API key does not match user id"}), 401
            
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            app.logger.error(f'User id: {current_user.id} || location: {fn} || error {e}')
            return jsonify({"msg": "Method unsuccessful"}), 400

    return decorator