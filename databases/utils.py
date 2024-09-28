from collections.abc import Iterable
from datetime import datetime

from flask import jsonify
from flask_jwt_extended import current_user

from .models import *
from constants import *

def check_type_and_format(val):
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return val

def serialize(res, keys):
    if isinstance(res, Iterable):
        return jsonify([{key:getattr(re, key) for key in keys} for re in res])
    return jsonify({key:getattr(res, key) for key in keys})

def join_camera(query):
    return query.join(Camera, Video.camera_id == Camera.id)

def join_action(query, is_outer=False):
    return query.join(Action, Video.action_id == Action.id, isouter=is_outer)

def join_location(query):
    return query.join(Location, Camera.location_id == Location.id)

def join_parent_child_detected(query, join_child=True):
    if join_child:
        return query.join(
            ParentChildDetected,
            Video.entry_id == ParentChildDetected.child,
            isouter=True)
    else:
        return query.join(
            ParentChildDetected,
            Video.entry_id == ParentChildDetected.parent,
            isouter=True)

def with_user_identity(query):
    return query.where(
        Video.user_id == current_user.id)

def filter_primary_videos(query):
    return query.where(
        Camera.is_primary == True,
        ParentChildDetected.parent == None)

def query_unreviewed_videos(query, location_id):
    query = join_camera(query)
    query = with_user_identity(query)
    query = query.where(
        Video.status == REVIEW_READY,
        Camera.location_id == location_id)

    return query

def query_history_videos(query, location_id):
    query = join_camera(query)
    query = join_action(query)
    query = with_user_identity(query)
    query = query.where(
        Video.status == REVIEW_DONE,
        Camera.location_id == location_id)

    return query