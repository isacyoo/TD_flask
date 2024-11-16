import logging
import logging.config
import os

import yaml
from flask import current_app as app
from sqlalchemy import select

from databases import Camera, ParentChildDetected, db

def configure_logging(config_path='logging.yaml', default_level=logging.INFO, env_key='INFER_LOG_CONFIG'):
    path = config_path
    value = os.getenv(env_key, None)
    if value:
        path = value

    logging.captureWarnings(True)

    if os.path.exists(path):
        with open(path, 'rt') as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
                logging.info('Logging configuration successful')
            except Exception as e:
                print(e)
                logging.error('Error in Logging Configuration. Using basicConfig')
                logging.basicConfig(level=default_level)
                logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.error('Failed to load logging configuration file. Using basicConfig')
        logging.basicConfig(level=default_level)
        logging.getLogger().setLevel(logging.DEBUG)

def has_all_keys(data, keys):
    return all([key in data for key in keys])
    
def extract_status_code(result):
    if isinstance(result, app.response_class):
        return result.status
    elif isinstance(result, tuple):
        return str(result[1])
    else:
        raise Exception(f"Unknown response type {type(result)}")