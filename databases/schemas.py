import json

from marshmallow import Schema, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow.fields import Nested, Field, Integer, String, DateTime, Url, Boolean, List
from sqlalchemy import select
from flask_jwt_extended import current_user

from .models import Action, Camera, Location, Video, Entry, Event, db, HighRiskMember, User
from utils.hours import WeekSchedule, InvalidScheduleException, convert_from_UTC

class JSONField(Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if isinstance(value, str):
            return json.loads(value)
        return value

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str):
            return json.loads(value)
        return value

class CustomDateTime(DateTime):
    def _serialize(self, value, attr, obj, **kwargs):
        if value:
            value = convert_from_UTC(value, current_user.timezone).replace(tzinfo=None)
        return super()._serialize(value, attr, obj, **kwargs)
    
class ActionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Action

class CameraSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Camera
        fields = ('id', 'name')

class ScheduleField(Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            value = {}
        try:
            week_schedule = WeekSchedule(value)
            return week_schedule.to_dict()
        except InvalidScheduleException:
            return {}

class LocationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Location
    
    cameras = Nested(CameraSchema, many=True)
    operational_hours = ScheduleField()

class VideoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Video

    uploaded_at = CustomDateTime(attribute="uploaded_at")

class EntrySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Entry

    videos = Nested(VideoSchema, many=True)
    entered_at = CustomDateTime(attribute="entered_at")

class EventSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Event


    entries = Nested(EntrySchema, many=True)
    location = Nested(LocationSchema, only=("id", "name"))
    action = Nested(ActionSchema)
    entered_at = CustomDateTime(attribute="entered_at")
    processed_at = CustomDateTime(attribute="processed_at")
    reviewed_at = CustomDateTime(attribute="reviewed_at")
    deleted_at = CustomDateTime(attribute="deleted_at")

class PageInfoSchema(Schema):
    total = Integer()
    page = Integer()
    pages = Integer()
    per_page = Integer()
    iter_pages = List(Integer())

class EventWithPageInfoSchema(Schema):
    events = Nested(EventSchema, many=True)
    page_info = Nested(PageInfoSchema)

class CountPerLocationSchema(Schema):
    location = Nested(LocationSchema, only=("id", "name"))
    count = Integer()

class EntryWebhookInputDataSchema(Schema):
    location_id = Integer(required=True)
    member_id = String(required=True)
    entered_at = DateTime()
    person_meta = JSONField()

    @validates('location_id')
    def check_location_exists(self, data, **kwargs):
        location = db.session.execute(
            select(Location).where(Location.user_id==current_user.id, Location.id==data)).scalar_one_or_none()
        
        if not location:
            raise ValidationError(f"Location {data} not found for user {current_user.id}")

class VideoPresignedUrlSchema(Schema):
    presigned_url = Url()
    video_id = String(required=True)

class EntryWebhookResponseSchema(Schema):
    videos = Nested(VideoPresignedUrlSchema, many=True, required=True)
    entry_id = String(required=True)

class StatsSchema(Schema):
    unreviewed = Integer()
    entries = Integer()
    in_process = Integer()

class LocationStatsSchema(Schema):
    location = Nested(LocationSchema, only=("id", "name"))
    stats = Nested(StatsSchema)

class StatsSchema(Schema):
    total_unreviewed = Integer()
    location_stats = Nested(LocationStatsSchema, many=True)


class HighRiskMemberSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = HighRiskMember

    created_at = CustomDateTime(attribute="created_at")

class UserSettingSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        fields = ("id", "name", "timezone", "is_admin", "api_key_expiry_date",
                  "video_retention_days", "stream_retention_hours", "review_high_risk_members")
        
    api_key_expiry_date = CustomDateTime(attribute="api_key_expiry_date")
        

class UpdateUserSettingInputSchema(Schema):
    video_retention_days = Integer()
    stream_retention_hours = Integer()
    review_high_risk_members = Boolean()

class UpdateLocationSettingInputSchema(Schema):
    name = String()
    video_retention_days = Integer(allow_none=True)
    stream_retention_hours = Integer(allow_none=True)
    review_high_risk_members = Boolean(allow_none=True)