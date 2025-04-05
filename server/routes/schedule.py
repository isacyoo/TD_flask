import os
import json

from flask import Blueprint, request, jsonify, current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, Location, Camera
from clients import sqs_client
from utils.auth import error_handler
from utils.hours import WeekSchedule, InvalidScheduleException

schedule = Blueprint("schedule", "__name__")

@schedule.get('/schedule/<location_id>')
@error_handler()
def get_location_schedule(location_id):
    location = db.session.execute(
        select(Location).where(Location.user_id==current_user.id, Location.id==location_id)).scalar_one_or_none()
    
    if not location:
        app.logger.info(f'Location id {location_id} not found with {current_user.id}')
        return jsonify({"msg": "Location not found"}), 404
    
    operational_hours = json.loads(location.operational_hours)
    try:
        schedule = WeekSchedule(operational_hours)
    except InvalidScheduleException:
        return jsonify({"msg": "Invalid schedule"}), 400
    
    valid = schedule.check_week_schedule_validity()

    if not valid:
        return jsonify({"msg": "Invalid schedule"}), 400

    return jsonify(schedule.to_dict()), 200

@schedule.post('/validate_schedule')
@error_handler()
def validate_schedule():
    schedule = request.json
    try:
        week_schedule = WeekSchedule(schedule)
    except InvalidScheduleException:
        return jsonify({"input_valid": False, "valid": False}), 200
    
    valid = week_schedule.check_week_schedule_validity()

    if not valid:
        return jsonify({"input_valid": True, "valid": False}), 200

    return jsonify({"input_valid": True, "valid": True}), 200
    

@schedule.post('/schedule/<location_id>')
@error_handler()
def modify_location_schedule(location_id):
    location = db.session.execute(
        select(Location).where(Location.user_id==current_user.id, Location.id==location_id)).scalar_one_or_none()

    if not location:
        app.logger.info(f'Location id {location_id} not found with {current_user.id}')
        return jsonify({"msg": "Location not found"}), 404
    
    new_schedule = request.json
    try:
        week_schedule = WeekSchedule(new_schedule)
    except InvalidScheduleException:
        app.logger.info(f'Invalid schedule with {current_user.id}')
        return jsonify({"msg": "Invalid schedule"}), 400
    
    valid = week_schedule.check_week_schedule_validity()

    if not valid:
        app.logger.info(f'Invalid schedule with {current_user.id}')
        return jsonify({"msg": "Invalid schedule"}), 400
    
    location.operational_hours = json.dumps(new_schedule)
    db.session.commit()

    if location.upload_method.value != 'RTSP':
        return jsonify({"msg": "Schedule updated"}), 201
    
    data_retention = location.stream_retention_hours
    timezone = current_user.timezone

    rtsp_details = [{
        'camera_id': camera.id,
        'stream_url': camera.stream_url,
        'data_retention': data_retention
    } for camera in location.cameras]

    location_info = {
        'location_id': location_id,
        'rtsp_details': rtsp_details,
        'timezone': timezone
    }

    message = {
        'location_info': location_info,
        'new_schedule': new_schedule
    }

    queue_url = sqs_client.get_queue_url(QueueName=os.getenv('UPDATE_SCHEDULE_QUEUE'))['QueueUrl']
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )

    return jsonify({"msg": "Schedule updated"}), 201