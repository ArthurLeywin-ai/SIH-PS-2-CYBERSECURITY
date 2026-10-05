"""14 Validation Gates package."""

from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.gates.gate_01_config import Gate01Configuration
from satsa_generator.validation.gates.gate_02_schema import Gate02SchemaBase
from satsa_generator.validation.gates.gate_03_referential import Gate03ReferentialIntegrity
from satsa_generator.validation.gates.gate_04_temporal import Gate04TemporalIntegrity
from satsa_generator.validation.gates.gate_05_missing_state import Gate05MissingStateSemantics
from satsa_generator.validation.gates.gate_06_scenario import Gate06ScenarioRealization
from satsa_generator.validation.gates.gate_07_authorized_mutation import Gate07AuthorizedMutation
from satsa_generator.validation.gates.gate_08_source_rendering import Gate08SourceRendering
from satsa_generator.validation.gates.gate_09_canonical_provenance import Gate09CanonicalProvenance
from satsa_generator.validation.gates.gate_10_distribution import Gate10DistributionSanity
from satsa_generator.validation.gates.gate_11_duplicate_behavior import Gate11DuplicateBehavior
from satsa_generator.validation.gates.gate_12_leakage import Gate12LeakageScan
from satsa_generator.validation.gates.gate_13_reproducibility import Gate13Reproducibility
from satsa_generator.validation.gates.gate_14_package_hash import Gate14PackageHash

ALL_GATES: tuple[type[ValidationGate], ...] = (
    Gate01Configuration,
    Gate02SchemaBase,
    Gate03ReferentialIntegrity,
    Gate04TemporalIntegrity,
    Gate05MissingStateSemantics,
    Gate06ScenarioRealization,
    Gate07AuthorizedMutation,
    Gate08SourceRendering,
    Gate09CanonicalProvenance,
    Gate10DistributionSanity,
    Gate11DuplicateBehavior,
    Gate12LeakageScan,
    Gate13Reproducibility,
    Gate14PackageHash,
)

__all__ = [
    "ALL_GATES",
    "Gate01Configuration",
    "Gate02SchemaBase",
    "Gate03ReferentialIntegrity",
    "Gate04TemporalIntegrity",
    "Gate05MissingStateSemantics",
    "Gate06ScenarioRealization",
    "Gate07AuthorizedMutation",
    "Gate08SourceRendering",
    "Gate09CanonicalProvenance",
    "Gate10DistributionSanity",
    "Gate11DuplicateBehavior",
    "Gate12LeakageScan",
    "Gate13Reproducibility",
    "Gate14PackageHash",
    "ValidationGate",
]
