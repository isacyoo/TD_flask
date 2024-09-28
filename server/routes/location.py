from flask import Blueprint, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user


from utils.auth import both_web_and_api
from databases import Location, serialize

location = Blueprint("location", "__name__")

@location.get("/locations")
@both_web_and_api
def get_locations() -> Response:
    keys = ["id", "name"]
    return serialize(Location.query.filter_by(user_id=current_user.id).all(), keys)   
    
@location.get("/location_id/<name>")
@both_web_and_api
def get_location_id(name) -> Response:
    keys = ["id", "name"]
    location = grab_location_id(current_user.id, name)
    if not location:
        app.logger.info(f'Location id {name} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {name} for user {current_user.id} not found"}), 404
    return serialize(location, keys)   
    
def grab_location_id(user_id, name):
    return Location.query.filter(Location.user_id==user_id, Location.name==name).limit(1)