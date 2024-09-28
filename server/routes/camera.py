from flask import Blueprint, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user

from utils.auth import both_web_and_api
from databases import Camera, serialize, Location

camera = Blueprint("camera", "__name__")

@camera.get("/cameras")
@both_web_and_api
def get_cameras() -> Response:
    keys = ["id", "name"]
    return serialize(Camera.query.filter_by(user_id=current_user.id).all(), keys)