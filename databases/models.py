from uuid import uuid4
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.pagination import Pagination
import sqlalchemy as sa
from sqlalchemy import MetaData

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
    
db = SQLAlchemy()

class UploadOptionEnum(Enum):
    UserUpload= 'UserUpload'
    RTSP = 'RTSP'
    Custom = 'Custom'

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(36), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(1024))
    is_admin = db.Column(db.Boolean, default=False)
    video_retention_period = db.Column(db.Integer, default=30)
    timezone = db.Column(db.String(40), default='Pacific/Auckland')
    
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(36), nullable=False)
    upload_method = db.Column(db.Enum(UploadOptionEnum), default=UploadOptionEnum.UserUpload, nullable=False)
    custom_upload_method = db.Column(db.String(256))
    operational_hours = db.Column(db.String(256))
    stream_retention_hours = db.Column(db.Integer, default=24)

    cameras = db.relationship("Camera", back_populates="location", innerjoin=True)

class Camera(db.Model):
    __table_args__ = (db.UniqueConstraint('location_id', 'name', name='_location_name_uc'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    display_order = db.Column(db.Integer)
    name = db.Column(db.String(36))
    threshold = db.Column(db.Float)
    x1 = db.Column(db.Float)
    y1 = db.Column(db.Float)
    x2 = db.Column(db.Float)
    y2 = db.Column(db.Float)
    x3 = db.Column(db.Float)
    y3 = db.Column(db.Float)
    x4 = db.Column(db.Float)
    y4 = db.Column(db.Float)
    nx = db.Column(db.Float)
    ny = db.Column(db.Float)

    location = db.relationship("Location", back_populates="cameras", innerjoin=True)
    
class Action(db.Model):
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_name_uc'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(36), nullable=False)
    is_tailgating = db.Column(db.Boolean)
    is_deleted = db.Column(db.Boolean)

class Event(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    processed_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), index=True)
    status = db.Column(db.Integer, index=True, nullable=False)

    entries = db.relationship("Entry", back_populates="event", innerjoin=True, lazy="joined")
    location = db.relationship("Location", innerjoin=True, lazy="joined")
    action = db.relationship("Action", lazy="joined")

    @property
    def entered_at(self):
        return min(entry.entered_at for entry in self.entries)

class Entry(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    event_id = db.Column(db.String(36), db.ForeignKey(Event.id), nullable=False, index=True)
    person_id = db.Column(db.String(36), index=True)
    person_meta = db.Column(db.String(1024), default="{}")
    entered_at = db.Column(db.DateTime)

    event = db.relationship("Event", back_populates="entries", innerjoin=True, lazy="joined")
    videos = db.relationship("Video", back_populates="entry", innerjoin=True, lazy="joined")
    

class Video(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False, index=True)
    camera_id = db.Column(db.Integer, db.ForeignKey(Camera.id), nullable=False)
    entry_id = db.Column(db.String(36), db.ForeignKey(Entry.id), index=True)
    status = db.Column(db.Integer, index=True, nullable=False)
    uploaded_at = db.Column(db.DateTime)

    entry = db.relationship("Entry", back_populates="videos", innerjoin=True, lazy="joined")
    
    def set_status(self, new_status):
        self.status = new_status
        db.session.commit()


class RTSPInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey(Camera.id), nullable=False, index=True)
    stream_url = db.Column(db.String(256), nullable=False)
    offset_amount = db.Column(db.Integer, default=0)