"""Supervisory Analytics Detectors Package."""

from app.backend.analytics.detectors.anomalies import StatisticalAnomalyDetector
from app.backend.analytics.detectors.attention import AttentionAggregator
from app.backend.analytics.detectors.execution_gaps import ExecutionGapDetector
from app.backend.analytics.detectors.negative_space import NegativeSpaceDetector
from app.backend.analytics.detectors.operational_drift import OperationalDriftDetector
from app.backend.analytics.detectors.peer_comparison import PeerComparisonDetector

__all__ = [
    "ExecutionGapDetector",
    "NegativeSpaceDetector",
    "StatisticalAnomalyDetector",
    "PeerComparisonDetector",
    "OperationalDriftDetector",
    "AttentionAggregator",
]
