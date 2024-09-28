from functools import wraps

from prometheus_client import Summary, Counter
from flask import current_app as app

from utils.misc import extract_status_code

REQUEST_TIME = Summary('flask_request_processing_seconds', 'Time spent processing request', ['method'])
FAILED_REQUEST = Counter('flask_failed_request_counter', 'Number of failed requests', ['method'])

def timeit(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        metric = REQUEST_TIME.labels(method.__name__)
        with metric.time():
            result = method(*args, **kwargs)
        return result
    return wrapper

def fail_counter(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        metric = FAILED_REQUEST.labels(method.__name__)
        result = method(*args, **kwargs)
        status_code = extract_status_code(result)
        if not status_code.startswith('2'):
            metric.inc(1)
        return result
    return wrapper