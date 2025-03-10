from sqlalchemy import select

from databases import db, Video

def get_video(id):
    video = db.session.execute(
        select(Video).where(Video.id==id)).unique().scalar_one_or_none()
    return video