import logging
import logging.config
import os

import yaml
from flask import current_app as app

def configure_logging(config_path='logging.yaml', default_level=logging.INFO):
    path = config_path

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

def has_all_keys(data, keys):
    return all([key in data for key in keys])
    
def extract_status_code(result):
    if isinstance(result, app.response_class):
        return result.status
    elif isinstance(result, tuple):
        return str(result[1])
    else:
        raise Exception(f"Unknown response type {type(result)}")
