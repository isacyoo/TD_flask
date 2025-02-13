from dataclasses import dataclass, field

@dataclass
class Stats:
    unreviewed: int = 0
    entries: int = 0
    in_process: int = 0

@dataclass
class LocationInfo:
    id: int
    name: str

@dataclass
class LocationStats:
    location: LocationInfo
    stats: Stats

    def set_stats(self, name, value):
        if hasattr(self.stats, name):
            setattr(self.stats, name, value)