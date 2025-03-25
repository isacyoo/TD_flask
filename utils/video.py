import os
import json

from sqlalchemy import select

from databases import db, Video
from clients import sqs_client

def get_video(id):
    video = db.session.execute(
        select(Video).where(Video.id==id)).unique().scalar_one_or_none()
    return video

def send_video_to_queue(video, camera):
    body = {
        "video_id": video.id,
        "gate": [(camera.x1, camera.y1), (camera.x2, camera.y2),
                 (camera.x3, camera.y3), (camera.x4, camera.y4)],
        "norm": [camera.nx, camera.ny],
        "threshold": camera.threshold,
        "minimum_time": camera.minimum_time
    }

    queue_url = sqs_client.get_queue_url(QueueName=os.getenv('VIDEO_PROCESSING_QUEUE'))['QueueUrl']
    res = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(body)
    )

    return res