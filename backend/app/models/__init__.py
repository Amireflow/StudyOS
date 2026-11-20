"""Modèles ORM SQLAlchemy 2 (Palier 1 & Palier 2 Lots 6-7)."""

from app.models.tables import (
    AiActionProposalTable,
    AiConversationTable,
    AiMessageTable,
    AiReportTable,
    LearningModuleTable,
    LearningPathTable,
    LessonTable,
    ProfileTable,
    ProjectTable,
    ScheduleEventTable,
    SkillEvidenceTable,
    SkillTable,
    StudySessionTable,
    TaskTable,
)

__all__ = [
    "ProfileTable",
    "TaskTable",
    "ScheduleEventTable",
    "StudySessionTable",
    "LearningPathTable",
    "LearningModuleTable",
    "LessonTable",
    "SkillTable",
    "SkillEvidenceTable",
    "ProjectTable",
    "AiConversationTable",
    "AiMessageTable",
    "AiActionProposalTable",
    "AiReportTable",
]
