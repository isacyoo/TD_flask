from flask import Blueprint, request, Response, jsonify
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, func
from werkzeug.exceptions import NotFound

from utils.auth import error_handler
from utils.metrics import timeit
from utils.event import retrieve_event
from databases import db, Location, query_events, get_page_info, Event, parse_time_range, query_adjacent_events, Entry
from databases.schemas import EventSchema, EventWithPageInfoSchema

event = Blueprint("event", "__name__")
PER_PAGE = 10


@event.get("/unreviewed_events/<location_id>")
@error_handler()
def get_all_unreviewed_events(location_id) -> Response:
    member_id = request.args.get("memberId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, member_id, time_range, None)
        
    events = db.session.execute(query).unique().scalars()
    events = EventSchema(many=True).dump(events)

    return jsonify(events)

@event.get("/unreviewed_events/<location_id>/<int:page>")
@timeit
@error_handler()
def get_unreviewed_events(location_id, page) -> Response:
    member_id = request.args.get("memberId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, member_id, time_range, None).group_by(Event.id)
    
    try:
        unreviewed_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = unreviewed_paginate.items
    page_info = get_page_info(unreviewed_paginate)
    res = {"events": events} | {"page_info": page_info}

    res = EventWithPageInfoSchema().dump(res)
    return jsonify(res)

@event.get("/history_events/<location_id>")
@error_handler()
def get_all_history_events(location_id) -> Response:
    action_ids = request.args.getlist("actionId", None)
    member_id = request.args.get("memberId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, member_id, time_range, action_ids, True)
    
    events = db.session.execute(query).unique().scalars()
    events = EventSchema(many=True).dump(events)
    
    return jsonify(events)

@event.get("/history_events/<location_id>/<int:page>")
@timeit
@error_handler()
def get_history_events(location_id, page) -> Response:
    action_ids = request.args.getlist("actionId", None)
    member_id = request.args.get("memberId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, member_id, time_range, action_ids, True).group_by(Event.id)

    try:
        history_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = history_paginate.items
    page_info = get_page_info(history_paginate)
    res = {"events": events} | {"page_info": page_info}
    res = EventWithPageInfoSchema().dump(res)

    return jsonify(res)
        
    
@event.get("/adjacent_events/<id>")
@error_handler(api=False)
def get_adjacent_events(id):
    action_id = request.args.get("actionId", None)
    member_id = request.args.get("memberId", None)

    current_event = retrieve_event(id)

    if not current_event:
        app.logger.info(f'Adjacent events could not be found as the events does not exist: {current_user.id} - {id}')
        return jsonify({"msg": "Event not found"}), 404

    if current_event.deleted_at:
        app.logger.info(f'Adjacent events could not be found as the event is deleted: {current_user.id} - {id}')
        return jsonify({"msg": "Event is deleted"}), 400
        
    next_event_query, previous_event_query = query_adjacent_events(current_event, member_id, action_id)
    
    next_event = db.session.execute(next_event_query).unique().scalars().first()
    previous_event = db.session.execute(previous_event_query).unique().scalars().first()
            
    if next_event:
        app.logger.debug(f'Next event of event {id} found - {next_event.id}')
        next_event = next_event.id
    
    if previous_event:
        app.logger.debug(f'Previous event of event {id} found - {previous_event.id}')
        previous_event = previous_event.id
        
    return jsonify({"next_event": next_event, "previous_event": previous_event})

@event.get("/event/<id>")
@error_handler()
def get_event_with_id(id) -> Response:
    event = retrieve_event(id)
    
    if not event:
        return jsonify({"msg": "Event not found"}), 404

    event = EventSchema().dump(event)
    
    return jsonify(event)


@event.get("/saved_events/<location_id>")
@error_handler()
def get_all_saved_events(location_id) -> Response:
    member_id = request.args.get("memberId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, member_id, time_range, None, saved=True)
    events = db.session.execute(query).unique().scalars()
    events = EventSchema(many=True).dump(events)
    
    return jsonify(events)

@event.get("/saved_events/<location_id>/<int:page>")
@error_handler()
def get_saved_events(location_id, page) -> Response:
    member_id = request.args.get("memberId", None)
    time_range = parse_time_range(request.args.get('time', None))

    query = query_events(location_id, member_id, time_range, None, saved=True).group_by(Event.id)

    try:
        saved_paginate = db.paginate(query, page=page, per_page=PER_PAGE)
    except NotFound:
        return jsonify({"msg": "No events found"}), 404
    
    events = saved_paginate.items
    page_info = get_page_info(saved_paginate)
    res = {"events": events} | {"page_info": page_info}
    res = EventWithPageInfoSchema().dump(res)
    
    return jsonify(res)

@event.put("/event_save_status/<id>")
@error_handler()
def update_event_save_status(id):
    save = request.json.get("save")
    event = retrieve_event(id)
    if not event:
        return jsonify({"msg": "Event not found"}), 404
    
    if save is None:
        return jsonify({"msg": "Save status not provided"}), 400
    
    event.is_saved = save
    db.session.commit()
    event = EventSchema().dump(event)
    
    return jsonify(event)