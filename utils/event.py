from sqlalchemy import select
from flask_jwt_extended import current_user

from databases import db, Location, Event

def retrieve_event(id):
    event = db.session.execute(
        select(Event).join(Location).where(
            Event.id==id,
            Location.user_id==current_user.id)).unique().scalars().one_or_none()

    return event