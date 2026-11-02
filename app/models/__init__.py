"""Shared OOP Domain Models across Subsystems S1, S2, and S3."""
from .activity_record import ActivityRecord
from .chat_message import ChatMessage
from .company import Company
from .department import Department
from .emission_factor import EmissionFactor
from .recommendation import Recommendation
from .target import ReductionTarget, Target
from .user import User

__all__ = [
    "Company",
    "Department",
    "EmissionFactor",
    "ActivityRecord",
    "Target",
    "ReductionTarget",
    "User",
    "ChatMessage",
    "Recommendation",
]
