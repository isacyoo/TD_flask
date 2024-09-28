import os
import json

from dotenv import load_dotenv
import boto3
if os.path.exists('./.env'):
    load_dotenv()

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
kvs_client = boto3.client('kinesisvideo')
scheduler = boto3.client('scheduler')
ecs_client = boto3.client('ecs')                      
resource_tagging_api = boto3.client('resourcegroupstaggingapi')                      
subnets = json.loads(os.getenv('SUBNETS'))