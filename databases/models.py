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
class CustomPagination(Pagination):

    def _query_items(self):
        select = self._query_args["select"]
        select = select.limit(self.per_page).offset(self._query_offset)
        session = self._query_args["session"]
        return list(session.execute(select))

    def _query_count(self):
        select = self._query_args["select"]
        sub = select.options(sa.orm.lazyload("*")).order_by(None).subquery()
        session = self._query_args["session"]
        out = session.execute(sa.select(sa.func.count()).select_from(sub)).scalar()
        return out

class CustomSQLAlchemy(SQLAlchemy):
    
    def paginate(
        self,
        select: sa.sql.Select,
        *,
        page: int | None = None,
        per_page: int | None = None,
        max_per_page: int | None = None,
        error_out: bool = True,
        count: bool = True,
    ) -> Pagination:
        return CustomPagination(
            select=select,
            session=self.session(),
            page=page,
            per_page=per_page,
            max_per_page=max_per_page,
            error_out=error_out,
            count=count,
        )
    
db = CustomSQLAlchemy()

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
    upload_method = db.Column(db.Enum(UploadOptionEnum), default='UserUpload', nullable=False)
    custom_upload_method = db.Column(db.String(256))
    operational_hours = db.Column(db.String(256))
    stream_retention_hours = db.Column(db.Integer, default=24)

class Camera(db.Model):
    __table_args__ = (db.UniqueConstraint('location_id', 'name', name='_location_name_uc'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(Location.id), nullable=False)
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
    is_primary = db.Column(db.Boolean, default=True, nullable=False)
    
class Action(db.Model):
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_name_uc'),)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False)
    name = db.Column(db.String(36), nullable=False)
    is_tailgating = db.Column(db.Boolean)
    is_deleted = db.Column(db.Boolean)
    
class StatusCode(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    status = db.Column(db.String(36), nullable=False, unique=True)
    
class Video(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=str(uuid4()), nullable=False, unique=True)
    user_id = db.Column(db.String(36), db.ForeignKey(User.id), nullable=False, index=True)
    camera_id = db.Column(db.Integer, db.ForeignKey(Camera.id), nullable=False)
    entry_id = db.Column(db.String(36), index=True)
    person_meta = db.Column(db.String(1024), default="{}")
    person_id = db.Column(db.String(36), index=True)
    status = db.Column(db.Integer, db.ForeignKey(StatusCode.id), index=True, nullable=False)
    entered_at = db.Column(db.DateTime)
    uploaded_at = db.Column(db.DateTime)
    processed_at = db.Column(db.DateTime)
    deleted_at = db.Column(db.DateTime)
    reviewed_at = db.Column(db.DateTime)
    action_id = db.Column(db.Integer, db.ForeignKey(Action.id), index=True)

    def set_status(self, new_status):
        self.status = new_status
        db.session.commit()
    
class ParentChildDetected(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    parent = db.Column(db.String(36), db.ForeignKey(Video.entry_id), nullable=False, unique=True, index=True)
    child = db.Column(db.String(36), db.ForeignKey(Video.entry_id), nullable=False, unique=True, index=True)

class RTSPInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey(Camera.id), nullable=False, index=True)
    stream_url = db.Column(db.String(256), nullable=False)
    offset_amount = db.Column(db.Integer, default=0)