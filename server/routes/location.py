from flask import Blueprint, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from utils.auth import error_handler
from databases import Location, serialize, db

location = Blueprint("location", "__name__")

@location.get("/locations")
@error_handler()
def get_locations() -> Response:
    keys = ["id", "name"]
    locations = db.session.execute(
        select(Location).where(Location.user_id==current_user.id)).scalars().all()
    return serialize(locations, keys)   
    
@location.get("/location_id/<name>")
@error_handler()
def get_location_id(name) -> Response:
    keys = ["id", "name"]
    location = grab_location_id(current_user.id, name)
    if not location:
        app.logger.info(f'Location id {name} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {name} for user {current_user.id} not found"}), 404
    return serialize(location, keys)   
    
def grab_location_id(user_id, name):
    location_id = db.session.execute(
        select(Location.id).where(
            Location.user_id==user_id,
            Location.name==name)).scalar_one_or_none()
    return location_id