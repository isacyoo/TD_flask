import os
import json

from clients import s3_client, sqs_client

def user_upload(video_ids, cameras):
    return [{"camera_name": camera.name} | s3_client.generate_presigned_post(Bucket=os.getenv('S3_BUCKET_NAME'),
                                            Key=f'/videos/{video_id}.mp4',
                                            ExpiresIn=600) for video_id, camera in zip(video_ids, cameras)]

def rtsp_upload(video_ids, streams, start_timestamps, end_timestamps):
    queue_url = sqs_client.get_queue_url(QueueName=os.getenv('VIDEO_CREATION_QUEUE'))['QueueUrl'],
    for video_id, stream, start_timestamp, end_timestamp in zip(video_ids,
                                                                streams,
                                                                start_timestamps,
                                                                end_timestamps):
        message = {
            "video": {"id": video_id},
            "stream_name": stream,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp
        }
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )