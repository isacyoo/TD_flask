from datetime import datetime, timedelta, timezone

from dataclasses import dataclass
from flask_jwt_extended import current_user

from databases import db, Location, Event, Entry
from sqlalchemy import select, func
from databases.schemas import CountPerLocationSchema
from utils.status_codes import EntryStatusCode

@dataclass
class Stats:
    unreviewed: int = 0
    entries: int = 0
    in_process: int = 0

@dataclass
class LocationInfo:
    id: int
    name: str

@dataclass
class LocationStats:
    location: LocationInfo
    stats: Stats

    def set_stats(self, name, value):
        if hasattr(self.stats, name):
            setattr(self.stats, name, value)

    
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
