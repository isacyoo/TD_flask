from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from flask_jwt_extended import current_user

from .models import *
from utils.status_codes import EventStatusCode

def query_videos(location_id, person_id, time_range, action_ids, history=False):
    if action_ids and not history:
        raise ValueError("Cannot query videos with action_ids without history=True")
    
    query = select(Event).join(Location).where(
        Location.user_id==current_user.id,
        Event.status==EventStatusCode.REVIEW_READY,
        Event.location_id==location_id
    )

    if history:
        query = query.where(Event.action_id.is_not(None))
    else:
        query = query.where(Event.action_id.is_(None))

    if person_id:
        query = query.where(Video.person_id==person_id)

    if time_range:
        start_time = datetime.now(timezone.utc) - timedelta(seconds=int(time_range))
        query = query.where(Video.entered_at > start_time)

    if action_ids:
        query = query.where(Event.action_id.in_(action_ids))
        
    query = query.order_by(
        Event.processed_at, Event.id.desc())
    
    return query


def get_page_info(paginate, iter_pages_count=3):
    iter_pages = list(paginate.iter_pages(left_current=iter_pages_count,
                                     right_current=iter_pages_count))
    return {
        "total": paginate.total,
        "page": paginate.page,
        "pages": paginate.pages,
        "per_page": paginate.per_page,
        "iter_pages": iter_pages
    }