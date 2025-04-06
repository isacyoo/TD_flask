from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, Action

def check_action_exists(action_name):
    action = db.session.execute(
        select(Action).where(
            Action.user_id == current_user.id,
            Action.name == action_name,
            Action.is_deleted==False)).scalars().one_or_none()
    
    return action is not None
