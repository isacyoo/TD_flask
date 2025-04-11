from flask import Blueprint, Response, jsonify, request
from flask import current_app as app
from flask_jwt_extended import current_user

from utils.auth import error_handler
from utils.stats import get_total_unreviewed_events_per_location, get_total_entries_per_location,\
    get_total_number_in_process_per_location, merge_stats
from databases import db
from databases.schemas import LocationSchema, StatsSchema, UpdateLocationSettingInputSchema
from utils.location import retrieve_location_id, retrieve_location, retrieve_locations

location = Blueprint("location", "__name__")

@location.get("/locations")
@error_handler()
def get_locations() -> Response:
    locations = retrieve_locations()
    
    locations = LocationSchema(many=True).dump(locations)

    return jsonify(locations), 200

@location.get("/location/<location_id>")
@error_handler()
def get_location(location_id) -> Response:
    location = retrieve_location(location_id)

    if not location:
        app.logger.info(f'Location id {location_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {location_id} for user {current_user.id} not found"}), 404

    return jsonify(LocationSchema().dump(location)), 200
    
@location.get("/location_id/<name>")
@error_handler()
def get_location_id(name) -> Response:
    location_id = retrieve_location_id(current_user.id, name)

    if not location_id:
        app.logger.info(f'Location id {name} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {name} for user {current_user.id} not found"}), 404

    return jsonify({"location_id": location_id}), 200

@location.get("/current_stats")
@error_handler()
def get_current_stats():
    hours = int(request.args.get("hours", "24"))

    unreviewed_events_per_location = get_total_unreviewed_events_per_location()
    total_unreviewed = sum([r["count"] for r in unreviewed_events_per_location])
    total_entries_per_location = get_total_entries_per_location(hours)
    total_in_process_per_location = get_total_number_in_process_per_location(hours)

    all_stats = merge_stats(unreviewed_events_per_location,
                            total_entries_per_location,
                            total_in_process_per_location)
    
    stats = StatsSchema().dump({"total_unreviewed": total_unreviewed,
                                         "location_stats": all_stats})
    
    return jsonify(stats)

@location.put("/location_settings/<location_id>")
@error_handler()
def update_location_settings(location_id) -> Response:
    data = UpdateLocationSettingInputSchema().load(request.json)
    location = retrieve_location(location_id)
    
    if not location:
        app.logger.info(f'Location id {location_id} not found | user id: {current_user.id}')
        return jsonify({"msg": f"Location {location_id} for user {current_user.id} not found"}), 404
    
    for key, value in data.items():
        setattr(location, key, value)
    
    db.session.commit()
    app.logger.info(f'Location id {location_id} updated | user id: {current_user.id}')
    
    res = LocationSchema().dump(location)
    return jsonify(res), 200