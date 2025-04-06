import datetime

from flask_jwt_extended import current_user
from sqlalchemy import select

from databases import db, HighRiskMember

def check_high_risk_member_exists(member_id):
    member = db.session.execute(
        select(HighRiskMember).where(
            HighRiskMember.user_id == current_user.id,
            HighRiskMember.member_id == member_id,
            HighRiskMember.is_deleted==False)).scalars().one_or_none()
    
    return member is not None