from enum import Enum

class VideoStatusCode(Enum):
    CREATED = "100"
    UPLOAD_IN_PROGRESS = "210"
    UPLOAD_FAILED = "410"
    PROCESS_READY = "120"
    REVIEW_READY = "130"
    DELETED = "900"

class EntryStatusCode(Enum):
    CREATED = "100"
    PROCESS_READY = "120"
    REVIEW_READY = "130"
    DELETED = "900"
