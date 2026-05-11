# backend/timeline/schemas.py
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class DetectedEvent:
    event_type: str
    severity: Severity
    reason: str
    recommended_action: str
