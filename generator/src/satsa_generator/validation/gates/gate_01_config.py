"""
Gate 1: Configuration Gate.

From GENERATOR_IMPLEMENTATION_PLAN §18.1:
- Tests: Type/schema, version compatibility, references, forbidden detector keys,
  private/public path separation.
- Failure condition: Any invalid/unresolved/forbidden config -> Stop.
"""

from __future__ import annotations

from satsa_generator.profiles.catalog import get_profile
from satsa_generator.validation.gates.base import ValidationGate
from satsa_generator.validation.models import (
    GateReport,
    GateSeverity,
    ValidationContext,
    ValidationIssue,
)


class Gate01Configuration(ValidationGate):
    """Gate 1: Validates generator configuration and detects forbidden keys."""

    @property
    def gate_index(self) -> int:
        return 1

    @property
    def gate_name(self) -> str:
        return "Configuration Gate"

    def validate(self, context: ValidationContext) -> GateReport:
        issues: list[ValidationIssue] = []
        cfg = context.config

        # 1. Version compatibility
        if not getattr(cfg, "generator_version", None):
            issues.append(
                ValidationIssue(
                    code="CONFIG_MISSING_VERSION",
                    severity=GateSeverity.BLOCKING,
                    gate_index=1,
                    gate_name=self.gate_name,
                    scope="config",
                    target="generator_version",
                    message="Missing generator_version in configuration",
                    expected="Non-empty generator version string",
                    actual=str(getattr(cfg, "generator_version", None)),
                )
            )

        # 2. Check forbidden detector keys (§18.1 Gate 1, §26)
        forbidden_keys = {
            "detector",
            "detector_threshold",
            "risk_score",
            "ml_model",
            "anomaly_threshold",
            "finding_weights",
            "classifier",
        }
        cfg_dict = cfg.model_dump(mode="json") if hasattr(cfg, "model_dump") else {}
        for key in cfg_dict:
            for forbidden in forbidden_keys:
                if forbidden in key.lower():
                    issues.append(
                        ValidationIssue(
                            code="CONFIG_FORBIDDEN_DETECTOR_KEY",
                            severity=GateSeverity.BLOCKING,
                            gate_index=1,
                            gate_name=self.gate_name,
                            scope="config",
                            target=key,
                            message=(
                                f"Forbidden detector/scoring key '{key}' found in configuration"
                            ),
                            expected="Generator configuration independent of detector logic",
                            actual=key,
                        )
                    )

        # 3. Reference resolution
        for org in getattr(cfg, "organizations", []):
            prof_name = getattr(org, "source_profile", None)
            if prof_name:
                try:
                    get_profile(prof_name)
                except Exception as exc:
                    issues.append(
                        ValidationIssue(
                            code="CONFIG_UNRESOLVED_PROFILE",
                            severity=GateSeverity.BLOCKING,
                            gate_index=1,
                            gate_name=self.gate_name,
                            scope=f"organization:{getattr(org, 'organization_id', 'unknown')}",
                            target=str(prof_name),
                            message=f"Source profile '{prof_name}' failed to resolve: {exc}",
                            expected="Registered profile in catalog",
                            actual=str(prof_name),
                        )
                    )

        return self.create_report(
            issues, metadata={"organization_count": len(getattr(cfg, "organizations", []))}
        )
