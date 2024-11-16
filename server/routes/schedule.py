import os
import json

from flask import Blueprint, request, jsonify, current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, serialize, Location, RTSPInfo, Camera
from clients import sqs_client
from utils.auth import both_web_and_api
from utils.hours import WeekSchedule

schedule = Blueprint("schedule", "__name__")

@schedule.get('/schedule')
@both_web_and_api
def get_all_schedule():
    all_locations = db.session.execute(
        select(Location).where(Location.user_id==current_user.id)).scalars().all()
    app.logger.debug(f'Get schedule for all locations successful with {current_user}')
    return serialize(all_locations, ['id', 'name', 'operational_hours'])

@schedule.get('/schedule/<location_id>')
@both_web_and_api
def get_location_schedule(location_id):
    location = get_location(location_id)    
    app.logger.debug(f'Get schedule for location {location_id} successful with {current_user}')
    return serialize(location, ['id', 'name', 'operational_hours'])

@schedule.post('/schedule/<location_id>')
@both_web_and_api
def modify_location_schedule(location_id):
    location = get_location(location_id)    
    if not location:
        app.logger.info(f'Location id {location_id} not found with {current_user.id}')
        return jsonify({"msg": "Location not found"}), 404
    
    if not location.upload_method == 'RTSP':
        app.logger.info(f'Location id {location_id} is not configured with RTSP')
        return jsonify({"msg": "Location not configured with RTSP"}), 400
    
    new_schedule = request.json
    week_schedule = WeekSchedule(new_schedule)
    valid = week_schedule.check_week_schedule_validity()
    if not valid:
        app.logger.info(f'Invalid schedule with {current_user.id}')
        return jsonify({"msg": "Invalid schedule"}), 400
    
    data_retention = location.stream_retention_hours
    timezone = current_user.timezone
    rtsp_details = db.session.execute(
        select(RTSPInfo).join(Camera).where(Camera.location_id==location_id)).all()

    rtsp_details = [{
        'camera_id': rtsp.camera_id,
        'stream_url': rtsp.stream_url,
        'data_retention': data_retention,
        'timezone': timezone
    } for rtsp in rtsp_details]

    location_info = {
        'location_id': location_id,
        'rtsp_details': rtsp_details
    }

    message = {
        'location_info': location_info,
        'new_schedule': new_schedule
    }

    queue_url = sqs_client.get_queue_url(QueueName=os.getenv('UPDATE_SCHEDULE_QUEUE'))['QueueUrl'],
    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )    

    return jsonify({"msg": "Schedule updated"}), 201

def get_location(location_id):
    location = db.session.execute(
        select(Location).where(Location.user_id==current_user.id, Location.id==location_id)).scalar_one_or_none()
    return location