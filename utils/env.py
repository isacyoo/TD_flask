import os

import boto3

from dotenv import load_dotenv

def get_secret(key):
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=key, WithDecryption=True)
    return response['Parameter']['Value']

def set_env_vars():
    if os.path.exists('./.env'):
        load_dotenv(override=True)

    os.environ['FLASK_SQLALCHEMY_DATABASE_URI'] = os.getenv('FLASK_SQLALCHEMY_DATABASE_URI', get_secret('SQLALCHEMY_DATABASE_URI'))
    os.environ['FLASK_JWT_SECRET_KEY'] = os.getenv('FLASK_JWT_SECRET_KEY', get_secret('JWT_SECRET_KEY'))
    
    os.environ['FLASK_SQLALCHEMY_ECHO'] = os.getenv('FLASK_SQLALCHEMY_ECHO', '0')
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = os.getenv('PROMETHEUS_MULTIPROC_DIR', '/tmp')

    os.environ['UPDATE_SCHEDULE_QUEUE'] = os.getenv('UPDATE_SCHEDULE_QUEUE', 'update-schedule')
    os.environ['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME', 'td.bucket')
    os.environ['VIDEO_CREATION_QUEUE'] = os.getenv('VIDEO_CREATION_QUEUE', 'video-creation')
    os.environ['VIDEO_PROCESSING_QUEUE'] = os.getenv('VIDEO_PROCESSING_QUEUE', 'video-processing')