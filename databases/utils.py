from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from flask_jwt_extended import current_user
from sqlalchemy.orm import lazyload

from .models import *

def query_events(location_id, member_id, time_range, action_ids, history=False, desc=True, saved=False):
    if action_ids and not history:
        raise ValueError("Cannot query videos with action_ids without history=True")

    query = select(Event).join(Location).join(Entry).where(
        Location.user_id==current_user.id,
        Event.deleted_at.is_(None),
        Event.location_id==location_id
    )

    if history:
        query = query.where(Event.action_id.is_not(None))
    else:
        query = query.where(Event.action_id.is_(None))

    if member_id:
        query = query.where(Entry.member_id==member_id)

    if time_range:
        start_time = datetime.now(timezone.utc) - timedelta(seconds=int(time_range))
        query = query.where(Entry.entered_at >= start_time)

    if action_ids:
        query = query.where(Event.action_id.in_(action_ids))

    if desc:
        query = query.order_by(
            Entry.entered_at.desc())
    else:
        query = query.order_by(
            Entry.entered_at)
        
    if saved:
        query = query.where(Event.is_saved==True)
    
    return query


def get_page_info(paginate, iter_pages_count=1):
    iter_pages = list(paginate.iter_pages(left_current=iter_pages_count,
                                     right_current=iter_pages_count))
    return {
        "total": paginate.total,
        "page": paginate.page,
        "pages": paginate.pages,
        "per_page": paginate.per_page,
        "iter_pages": iter_pages
    }

def parse_time_range(time_range):
    if not time_range:
        return None
    unit = time_range[-1]
    if unit == 'h':
        return int(time_range[:-1])*60*60
    elif unit == 'd':
        return int(time_range[:-1])*60*60*24
    elif unit == 'w':
        return int(time_range[:-1])*60*60*24*7
    
    return None

def query_adjacent_events(current_event, member_id, action_ids):
    history = current_event.action_id is not None
    
    next_query = query_events(current_event.location_id, member_id, None, action_ids, history).where(
        Entry.entered_at < current_event.entered_at,
        Event.id != current_event.id
    ).limit(1)

    prev_query = query_events(current_event.location_id, member_id, None, action_ids, history, desc=False).where(
        Entry.entered_at > current_event.entered_at,
        Event.id != current_event.id
    ).limit(1)

    return next_query, prev_query
