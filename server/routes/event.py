from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, func
from werkzeug.exceptions import NotFound

from utils.auth import error_handler
from utils.metrics import timeit
from utils.status_codes import EventStatusCode
from databases import db, Location, query_events, get_page_info, Event, parse_time_range, query_adjacent_events
from databases.schemas import EventSchema, EventsPerLocationSchema

event = Blueprint("event", "__name__")
PER_PAGE = 1


@event.get("/all_unreviewed_events/<location_id>")
@error_handler()
def get_all_unreviewed_events(location_id) -> Response:
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, person_id, time_range, None)
        
    events = db.session.execute(query).unique().scalars()
    events = EventSchema(many=True).dump(events)

    return jsonify(events)

@event.get("/unreviewed_events/<location_id>/<int:page>")
@timeit
@error_handler()
def get_unreviewed_events(location_id, page) -> Response:
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, person_id, time_range, None)
    
    try:
        unreviewed_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = EventSchema(many=True).dump(unreviewed_paginate.items)
    page_info = get_page_info(unreviewed_paginate)
    res = {"events": events} | page_info

    return jsonify(res)

@event.get("/all_history_events/<location_id>")
@error_handler()
def get_all_history_events(location_id) -> Response:
    action_ids = request.args.getlist("actionId", None)
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, person_id, time_range, action_ids, True)
    
    events = db.session.execute(query).unique().scalars()
    events = EventSchema(many=True).dump(events)
    
    return jsonify(events)

@event.get("/history_events/<location_id>/<int:page>")
@timeit
@error_handler()
def get_history_events(location_id, page) -> Response:
    action_ids = request.args.getlist("actionId", None)
    person_id = request.args.get("personId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, person_id, time_range, action_ids, True)

    try:
        history_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = EventSchema(many=True).dump(history_paginate.items)
    page_info = get_page_info(history_paginate)
    res = {"events": events} | page_info

    return jsonify(res)
        
    
@event.get("/adjacent_events/<id>")
@error_handler(api=False)
def get_adjacent_events(id):
    action_id = request.args.get("actionId", None)
    person_id = request.args.get("personId", None)

    current_event = db.session.execute(
        select(Event).join(Location).where(
            Event.id==id,
            Location.user_id==current_user.id)).unique().scalars().one_or_none()

    if not current_event:
        app.logger.info(f'Adjacent events could not be found as the events does not exist: {current_user.id} - {id}')
        return jsonify({"msg": "Event not found"}), 404
    
    if not current_event.status == EventStatusCode.REVIEW_READY:
        app.logger.info(f'Adjacent events could not be found as the event status is not valid: {current_user.id} - {id}')
        return jsonify({"msg": "Event status not valid"}), 400
    
    next_event_query, previous_event_query = query_adjacent_events(current_event, person_id, action_id)
    
    next_event = db.session.execute(next_event_query).unique().scalars().first()
    previous_event = db.session.execute(previous_event_query).unique().scalars().first()
            
    if next_event:
        app.logger.debug(f'Next event of event {id} found - {next_event.id}')
        next_event = next_event.id
    
    if previous_event:
        app.logger.debug(f'Previous event of event {id} found - {previous_event.id}')
        previous_event = previous_event.id
        
    return jsonify({"next_event": next_event, "previous_event": previous_event})

@event.get("/total_unreviewed_events")
@error_handler()
def get_total_unreviewed_events():
    query = select(func.count()).select_from(Event).join(Location).where(
        Location.user_id==current_user.id,
        Event.status==EventStatusCode.REVIEW_READY,
        Event.action_id.is_(None))

    res = db.session.execute(query).scalar()
    return jsonify({"total_unreviewed": res})

@event.get("/total_unreviewed_events_per_location")
@error_handler()
def get_total_unreviewed_events_per_location():
    query = select(Location, func.count()).select_from(Event).join(Location).where(
        Location.user_id==current_user.id,
        Event.status==EventStatusCode.REVIEW_READY,
        Event.action_id.is_(None)).group_by(Location.id)
    
    res = db.session.execute(query).all()
    
    return EventsPerLocationSchema(many=True).dump({"location": r[0], "count": r[1]} for r in res)