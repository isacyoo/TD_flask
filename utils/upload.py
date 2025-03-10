import os
import json

from clients import s3_client, sqs_client

def generate_presigned_url(video_id):
    return s3_client.generate_presigned_url_post(Bucket=os.getenv('S3_BUCKET_NAME'),
                                                    Key=f'/videos/{video_id}.mp4',
                                                    ExpiresIn=600)

def user_upload(videos):
    presigned_urls = [{"presigned_url": generate_presigned_url(video.id), "video_id": video.id} for video in videos]
    
    return presigned_urls

def rtsp_upload(videos, streams, start_timestamps, end_timestamps):
    queue_url = sqs_client.get_queue_url(QueueName=os.getenv('VIDEO_CREATION_QUEUE'))['QueueUrl']
    for video, stream, start_timestamp, end_timestamp in zip(videos,
                                                                streams,
                                                                start_timestamps,
                                                                end_timestamps):
        message = {
            "video": {"id": video.id},
            "stream_name": str(stream),
            "start_timestamp": start_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "end_timestamp": end_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )