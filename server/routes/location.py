from datetime import datetime, timezone, timedelta

from flask import Blueprint, Response, jsonify, request
from flask import current_app as app
from flask_jwt_extended import current_user
from sqlalchemy import select, func

from utils.auth import error_handler
from databases import Location, db, Event, Entry
from databases.schemas import LocationSchema, CountPerLocationSchema, StatsSchema
from utils.status_codes import EntryStatusCode
from utils.stats import LocationStats, LocationInfo, Stats

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


def get_total_unreviewed_events():
    query = select(func.count()).select_from(Event).join(Location).where(
        Location.user_id==current_user.id,
        Event.deleted_at.is_(None),
        Event.action_id.is_(None))

    return db.session.execute(query).scalar()

def get_total_unreviewed_events_per_location():
    query = select(Location, func.count(Event.id)).select_from(Location).join(Event, isouter=True).where(
        Location.user_id==current_user.id,
        Event.deleted_at.is_(None),
        Event.action_id.is_(None)).group_by(Location.id)
    
    res = db.session.execute(query).all()
    
    return CountPerLocationSchema(many=True).dump({"location": r[0], "count": r[1]} for r in res)

def get_total_entries_per_location(hours):
    query = select(Location, func.count()).select_from(Location).join(Event).join(Entry).where(
        Location.user_id==current_user.id,
        Entry.entered_at >= datetime.now(timezone.utc) - timedelta(hours=hours)).group_by(Location.id)
    
    res = db.session.execute(query).all()
    
    return CountPerLocationSchema(many=True).dump({"location": r[0], "count": r[1]} for r in res)

def get_total_number_in_process_per_location(hours):
    query = select(Location, func.count()).select_from(Location).join(Event).join(Entry).where(
        Location.user_id==current_user.id,
        Entry.status.in_([EntryStatusCode.CREATED, EntryStatusCode.PROCESS_READY]),
        Entry.entered_at >= datetime.now(timezone.utc) - timedelta(hours=hours)).group_by(Location.id)
    
    res = db.session.execute(query).all()
    
    return CountPerLocationSchema(many=True).dump({"location": r[0], "count": r[1]} for r in res)

def merge_stats(unreviewed, entries, in_process):
    all_stats = {}

    def update_stats(location, stats_name, count):
        if location["id"] in all_stats:
            setattr(all_stats[location["id"]].stats, stats_name, count)
        else:
            all_stats[location["id"]] = LocationStats(location=LocationInfo(**location),
                                                      stats=Stats(**{stats_name: count}))

    for r in unreviewed:
        update_stats(r["location"], "unreviewed", r["count"])

    for r in entries:
        update_stats(r["location"], "entries", r["count"])

    for r in in_process:
        update_stats(r["location"], "in_process", r["count"])

    return list(all_stats.values())


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