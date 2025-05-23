from uuid import uuid4
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

from utils.status_codes import EntryStatusCode, VideoStatusCode

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
    api_key_expiry_date = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)
    video_retention_days = db.Column(db.Integer, default=30)
    stream_retention_hours = db.Column(db.Integer, default=24)
    timezone = db.Column(db.String(40), default='Pacific/Auckland')
    review_high_risk_members = db.Column(db.Boolean, default=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    address = db.Column(db.String(200), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

class Location(db.Model):
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_name_uc'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(36), nullable=False)
    upload_method = db.Column(db.Enum(UploadOptionEnum), default=UploadOptionEnum.UserUpload, nullable=False)
    custom_upload_method = db.Column(db.String(256))
    operational_hours = db.Column(db.JSON)
    video_retention_days = db.Column(db.Integer, default=30)
    stream_retention_hours = db.Column(db.Integer, default=24)
    review_high_risk_members = db.Column(db.Boolean, default=False)

    cameras = db.relationship("Camera", back_populates="location", innerjoin=True)

class Camera(db.Model):
    __table_args__ = (db.UniqueConstraint('location_id', 'name', name='_location_name_uc'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    display_order = db.Column(db.Integer)
    name = db.Column(db.String(36))
    threshold = db.Column(db.Float)
    minimum_time = db.Column(db.Float)
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
    stream_url = db.Column(db.String(256))
    offset_amount = db.Column(db.Integer, default=0)

    location = db.relationship("Location", back_populates="cameras", innerjoin=True)
    
class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(36), nullable=False)
    is_tailgating = db.Column(db.Boolean)
    is_enabled = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False)


class HighRiskMember(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False)
    member_id = db.Column(db.String(36), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False)


class Event(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
    processed_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    is_merged = db.Column(db.Boolean, default=False)
    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), index=True)
    is_saved = db.Column(db.Boolean, default=False)
    comment = db.Column(db.String(256), default="")

    entries = db.relationship("Entry", back_populates="event", innerjoin=True, lazy="joined")
    location = db.relationship("Location", innerjoin=True, lazy="joined")
    action = db.relationship("Action", lazy="joined")

    @property
    def entered_at(self):
        return min(entry.entered_at for entry in self.entries)

class Entry(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    event_id = db.Column(db.String(36), db.ForeignKey(Event.id), index=True, nullable=False)
    member_id = db.Column(db.String(36), index=True)
    member_meta = db.Column(db.JSON)
    entered_at = db.Column(db.DateTime)
    status = db.Column(db.Enum(EntryStatusCode, values_callable=lambda c: [e.value for e in c]),
                       default=EntryStatusCode.CREATED, index=True, nullable=False)

    event = db.relationship("Event", back_populates="entries", innerjoin=True, lazy="joined")
    videos = db.relationship("Video", back_populates="entry", innerjoin=True, lazy="joined")
    

class Video(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    camera_id = db.Column(db.Integer, db.ForeignKey(Camera.id), nullable=False)
    entry_id = db.Column(db.String(36), db.ForeignKey(Entry.id), index=True)
    status = db.Column(db.Enum(VideoStatusCode, values_callable=lambda c: [e.value for e in c]),
                       default=VideoStatusCode.CREATED, index=True, nullable=False)
    uploaded_at = db.Column(db.DateTime)

    entry = db.relationship("Entry", back_populates="videos", innerjoin=True, lazy="joined")
    
    def set_status(self, new_status):
        self.status = new_status
        db.session.commit()