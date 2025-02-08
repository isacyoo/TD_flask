from flask import Blueprint, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from utils.auth import error_handler
from databases import Location, db
from databases.schemas import LocationSchema

location = Blueprint("location", "__name__")

@location.get("/locations")
@error_handler()
def get_locations() -> Response:
    locations = db.session.execute(
        select(Location).where(Location.user_id==current_user.id)).scalars().all()
    
    locations = LocationSchema(many=True).dump(locations)

    return jsonify(locations), 200

@location.get("/location/<location_id>")
@error_handler()
def get_location(location_id) -> Response:
    location = db.session.execute(
        select(Location).where(Location.id==location_id)).scalars().one_or_none()

    if not location:
        app.logger.info(f'Location id {location_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {location_id} for user {current_user.id} not found"}), 404

    return jsonify(LocationSchema().dump(location)), 200
    
@location.get("/location_id/<name>")
@error_handler()
def get_location_id(name) -> Response:
    location_id = grab_location_id(current_user.id, name)

    if not location_id:
        app.logger.info(f'Location id {name} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {name} for user {current_user.id} not found"}), 404

    return jsonify({"location_id": location_id}), 200

    
def grab_location_id(user_id, name):
    location_id = db.session.execute(
        select(Location.id).where(
            Location.user_id==user_id,
            Location.name==name)).scalar_one_or_none()
    
    return location_id