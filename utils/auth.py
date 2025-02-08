from functools import wraps
from re import split
import traceback

from passlib.hash import sha256_crypt
from flask import current_app as app, jsonify
from flask import request
from flask_jwt_extended import get_jwt, verify_jwt_in_request, current_user
from sqlalchemy import select

from databases import User, db
    
def validate_login(id, password):
    user = db.session.execute(
        select(User).where(User.id == id)).scalar_one_or_none()
    if not user:
        return False, None
    verified = sha256_crypt.verify(password, user.password)
    
    return verified, user

def error_handler(web=True, api=True, admin=False):
    def inner(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if web and not api:
                if claims.get("is_api"):
                    app.logger.warning('This endpoint is not intended for API use')
                    return jsonify({"msg": "This endpoint is not intended for API use"}), 401
            if api and not web:
                if not claims.get("is_api"):
                    app.logger.warning('This endpoint is not intended for web use')
                    return jsonify({"msg": "This endpoint is not intended for web use"}), 401
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