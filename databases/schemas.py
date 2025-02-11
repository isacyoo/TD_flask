import json

from marshmallow import Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow.fields import Nested, Field, Integer

from .models import *

class JSONField(Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None or value == '':
            return {}
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

class EventsPerLocationSchema(Schema):
    location = Nested(LocationSchema, only=("id", "name"))
    count = Integer()