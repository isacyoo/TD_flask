import os

import boto3

from dotenv import load_dotenv

def get_secret(key):
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=key, WithDecryption=True)
    return response['Parameter']['Value']

def get_default_db_uri(demo=False):
    if demo:
        s3 = boto3.client('s3')
        demo_db_bucket = os.getenv('S3_BUCKET_NAME', 'td.bucket')
        demo_db_key = os.getenv('DEMO_DB_KEY', 'demo/demo.db')
        if demo_db_bucket and demo_db_key:
            if not os.path.exists('./instance/demo.db'):
                os.makedirs('./instance', exist_ok=True)
                s3.download_file(demo_db_bucket, demo_db_key, './instance/demo.db')

        return 'sqlite:///demo.db'
    else:
        return get_secret('SQLALCHEMY_DATABASE_URI')

def set_env_vars():
    if os.path.exists('./.env'):
        load_dotenv(override=True)

    os.environ['DEMO_ENVIRONMENT'] = os.getenv('DEMO_ENVIRONMENT', '0')
    demo = os.getenv('DEMO_ENVIRONMENT', '0') == '1'

    os.environ['FLASK_SQLALCHEMY_DATABASE_URI'] = os.getenv('FLASK_SQLALCHEMY_DATABASE_URI', get_default_db_uri(demo))
    os.environ['FLASK_JWT_SECRET_KEY'] = os.getenv('FLASK_JWT_SECRET_KEY', get_secret('JWT_SECRET_KEY'))
    
    os.environ['FLASK_SQLALCHEMY_ECHO'] = os.getenv('FLASK_SQLALCHEMY_ECHO', '0')
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = os.getenv('PROMETHEUS_MULTIPROC_DIR', '/tmp')

    os.environ['UPDATE_SCHEDULE_QUEUE'] = os.getenv('UPDATE_SCHEDULE_QUEUE', 'update-schedule')
    os.environ['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME', 'td.bucket')
    os.environ['VIDEO_CREATION_QUEUE'] = os.getenv('VIDEO_CREATION_QUEUE', 'video-creation')
    os.environ['VIDEO_PROCESSING_QUEUE'] = os.getenv('VIDEO_PROCESSING_QUEUE', 'video-processing')