from databases import Location, db
from sqlalchemy import select
from flask_jwt_extended import current_user

def retrieve_location(location_id):
    location = db.session.execute(
        select(Location).where(
            Location.user_id == current_user.id,
            Location.id == location_id)).scalars().one_or_none()
    
    return location

def retrieve_locations():
    locations = db.session.execute(
        select(Location).where(
            Location.user_id == current_user.id)).scalars().all()
    
    return locations

def retrieve_location_id(user_id, name):
    location_id = db.session.execute(
        select(Location.id).where(
            Location.user_id==user_id,
            Location.name==name)).scalar_one_or_none()
    
    return location_id