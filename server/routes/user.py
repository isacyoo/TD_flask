from flask import Blueprint, request, Response, jsonify, session
from flask import current_app as app
from utils.auth import admin_required
import random

from databases import db, User

users = Blueprint("users", "__name__")

@users.post("/user")
@admin_required
def create_user() -> Response:
    data = request.get_json()
    db.session.add(User(**data))
    db.session.commit()
    return jsonify({"msg": f"Successfully created user {data['id']}"}), 201