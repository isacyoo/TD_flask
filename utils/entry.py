import json

from marshmallow import ValidationError
from flask import current_app as app
from flask_jwt_extended import current_user

from databases.schemas import EntryWebhookInputDataSchema
from utils.hours import WeekSchedule

def parse_input_data(data):
    try:
        result = EntryWebhookInputDataSchema().load(data)
        return result
    except ValidationError as e:
        app.logger.info(f"Error parsing JSON data: {e}")
        return None
    
def check_operational(location, current_time):
    operational_hours = location.operational_hours

    if not operational_hours:
        app.logger.info(f"Operational hours not found for location {location.name}")
        return False
        
    week_schedule = WeekSchedule(json.loads(operational_hours))
    is_operational = week_schedule.check_operational(current_time, current_user.timezone, False, False)

    return is_operational