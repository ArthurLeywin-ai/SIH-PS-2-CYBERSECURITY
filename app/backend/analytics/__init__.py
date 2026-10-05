"""SAT-SA Supervisory Analytics Engine Package.

Provides deterministic, auditable, explainable analytics across canonical operational evidence:
- Execution Gap Analytics
- Negative Space Analytics
- Statistical Anomaly Detection
- Peer Comparison Cohort Analytics
- Operational Drift Analysis
- Entity Attention Aggregation
"""

from app.backend.analytics.engine import SupervisoryAnalyticsEngine
from app.backend.analytics.evidence import EvidenceResolver
from app.backend.analytics.features import EntityPeriodFeatures, FeatureExtractor
from app.backend.analytics.models import (
    AnalyticsRunResult,
    EvidenceReference,
    EvidenceRole,
    SignalSeverity,
    SignalType,
    SupervisoryAttentionSummary,
    SupervisoryAttentionSummaryModel,
    SupervisorySignal,
    SupervisorySignalModel,
)
from app.backend.analytics.repository import AnalyticsRepository

__all__ = [
    "SupervisoryAnalyticsEngine",
    "AnalyticsRepository",
    "EvidenceResolver",
    "FeatureExtractor",
    "EntityPeriodFeatures",
    "SignalType",
    "SignalSeverity",
    "EvidenceRole",
    "EvidenceReference",
    "SupervisorySignal",
    "SupervisoryAttentionSummary",
    "AnalyticsRunResult",
    "SupervisorySignalModel",
    "SupervisoryAttentionSummaryModel",
]
