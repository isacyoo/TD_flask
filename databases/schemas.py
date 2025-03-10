import json

from marshmallow import Schema, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow.fields import Nested, Field, Integer, String, DateTime, Url
from sqlalchemy import select
from flask_jwt_extended import current_user

from .models import Action, Camera, Location, Video, Entry, Event, db

class JSONField(Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None or value == '':
            return {}
        return json.loads(value)
    
    def _deserialize(self, value, attr, data, **kwargs):
        return json.loads(value)
        
class ActionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Action

class CameraSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Camera
        fields = ('id', 'name')

class LocationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Location
    
    cameras = Nested(CameraSchema, many=True)
    operational_hours = JSONField()

class VideoSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Video

class EntrySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Entry

    videos = Nested(VideoSchema, many=True)
    person_meta = JSONField()

class EventSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Event


    entries = Nested(EntrySchema, many=True)
    location = Nested(LocationSchema, only=("id", "name"))
    action = Nested(ActionSchema)
    entered_at = DateTime(attribute="entered_at")

class CountPerLocationSchema(Schema):
    location = Nested(LocationSchema, only=("id", "name"))
    count = Integer()

class EntryWebhookInputDataSchema(Schema):
    location_id = Integer(required=True)
    person_id = String(required=True)
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