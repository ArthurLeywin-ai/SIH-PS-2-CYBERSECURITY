"""
M4 — Scenario and Legitimate-Control Engine.

This package implements the scenario-generation layer that creates
controlled operational conditions (concerning, legitimate-unusual,
ambiguous, normal) within the M2 base world. All scenario metadata,
authorization records, and ground truth remain strictly private.
"""

from __future__ import annotations

from satsa_generator.scenarios.catalog import (
    CATALOG_VERSION,
    get_catalog,
    get_scenario,
    get_scenarios_by_family,
    validate_catalog,
)
from satsa_generator.scenarios.controls import LegitimateControlEngine
from satsa_generator.scenarios.engine import (
    ScenarioEngine,
    ScenarioEngineError,
    ScenarioExecutionResult,
)
from satsa_generator.scenarios.ledger import (
    AuthorizationError,
    AuthorizationLedger,
)
from satsa_generator.scenarios.models import (
    AuthorizationEntry,
    AuthorizationStatus,
    ControlContextType,
    GroundTruthRecord,
    LegitimateControlDeclaration,
    MutationReceipt,
    MutationType,
    RealizationState,
    ScenarioDefinition,
    ScenarioFamily,
    ScenarioPlan,
    TruthRecordRole,
)
from satsa_generator.scenarios.mutators import (
    MutationError,
    ScenarioMutator,
)
from satsa_generator.scenarios.selectors import (
    ScenarioSelector,
    SelectionError,
)
from satsa_generator.scenarios.truth import (
    GroundTruthWriter,
    LeakageError,
    LeakageScanner,
)
from satsa_generator.scenarios.validators import (
    ScenarioValidationError,
    ScenarioValidationReport,
    ScenarioValidator,
)

__all__ = [
    "CATALOG_VERSION",
    "AuthorizationEntry",
    "AuthorizationError",
    "AuthorizationLedger",
    "AuthorizationStatus",
    "ControlContextType",
    "GroundTruthRecord",
    "GroundTruthWriter",
    "LeakageError",
    "LeakageScanner",
    "LegitimateControlDeclaration",
    "LegitimateControlEngine",
    "MutationError",
    "MutationReceipt",
    "MutationType",
    "RealizationState",
    "ScenarioDefinition",
    "ScenarioEngine",
    "ScenarioEngineError",
    "ScenarioExecutionResult",
    "ScenarioFamily",
    "ScenarioMutator",
    "ScenarioPlan",
    "ScenarioSelector",
    "ScenarioValidationError",
    "ScenarioValidationReport",
    "ScenarioValidator",
    "SelectionError",
    "TruthRecordRole",
    "get_catalog",
    "get_scenario",
    "get_scenarios_by_family",
    "validate_catalog",
]
