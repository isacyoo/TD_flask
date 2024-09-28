import logging
import logging.config
import os

import yaml
from flask import current_app as app

from databases import Camera, ParentChildDetected

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

def video_is_primary(video):
    camera = Camera.query.filter_by(id=video.camera_id).one_or_none()
    parent = ParentChildDetected.query.filter_by(child=video.entry_id).one_or_none()
    if not parent and camera.is_primary:
        return True
    
    return False

def has_all_keys(data, keys):
    return all([key in data for key in keys])
    
def extract_status_code(result):
    if isinstance(result, app.response_class):
        return result.status
    elif isinstance(result, tuple):
        return str(result[1])
    else:
        raise Exception(f"Unknown response type {type(result)}")