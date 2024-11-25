import os
import json

from dotenv import load_dotenv
import boto3
if os.path.exists('./.env'):
    load_dotenv()

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')