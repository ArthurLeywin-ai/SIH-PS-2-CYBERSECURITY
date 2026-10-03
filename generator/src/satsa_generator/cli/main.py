"""
CLI entry point — orchestrates approved generator commands.

From GENERATOR_IMPLEMENTATION_PLAN §2.2:
- Use argparse initially. Typer/Rich are unnecessary unless later usability
  testing justifies them.
- CLI flags select configuration files/versions, output root, and safe
  runtime limits — not distributions or scenario truth ad hoc.
- Environment variables may specify paths and private seed input only.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("satsa_generator")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the generator CLI."""
    parser = argparse.ArgumentParser(
        prog="satsa-gen",
        description=(
            "SAT-SA Synthetic Dataset Generator — "
            "deterministic, offline, reproducible."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- validate-config ---
    validate_parser = subparsers.add_parser(
        "validate-config",
        help="Validate a configuration file without generating data.",
    )
    validate_parser.add_argument(
        "config_path",
        type=Path,
        help="Path to configuration file (.json or .toml)",
    )

    # --- freeze-config ---
    freeze_parser = subparsers.add_parser(
        "freeze-config",
        help="Freeze configuration and print canonical hash.",
    )
    freeze_parser.add_argument(
        "config_path",
        type=Path,
        help="Path to configuration file (.json or .toml)",
    )
    freeze_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path for frozen canonical JSON.",
    )

    # --- generate ---
    generate_parser = subparsers.add_parser(
        "generate",
        help="Run dataset generation (placeholder — not yet implemented).",
    )
    generate_parser.add_argument(
        "config_path",
        type=Path,
        help="Path to configuration file (.json or .toml)",
    )
    generate_parser.add_argument(
        "--seed",
        type=str,
        default=None,
        help="Hex-encoded 256-bit master seed (or set SATSA_MASTER_SEED env var).",
    )

    fixture_parser = subparsers.add_parser(
        "build-fixture",
        help="Build the tiny deterministic Milestone 1 operational fixture.",
    )
    fixture_parser.add_argument(
        "config_path",
        type=Path,
        help="Path to the deterministic fixture configuration.",
    )
    fixture_parser.add_argument(
        "--seed",
        type=str,
        default=None,
        help="Hex-encoded 256-bit master seed (or SATSA_MASTER_SEED).",
    )
    fixture_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Runtime output directory override (must be absent or empty).",
    )

    return parser


def cmd_validate_config(args: argparse.Namespace) -> int:
    """Validate a configuration file."""
    from satsa_generator.config.models import load_config

    try:
        config = load_config(args.config_path)
        config_hash = config.config_hash()
        print("✓ Configuration valid.")
        print(f"  Hash: {config_hash}")
        print(f"  Organizations: {len(config.organizations)}")
        print(f"  Periods: {len(config.periods)}")
        print(f"  Tier: {config.tier.value}")
        print(f"  Split: {config.split.value}")
        return 0
    except Exception as e:
        print(f"✗ Configuration invalid: {e}", file=sys.stderr)
        return 1


def cmd_freeze_config(args: argparse.Namespace) -> int:
    """Freeze configuration and output canonical JSON + hash."""
    from satsa_generator.config.models import freeze_config, load_config

    try:
        config = load_config(args.config_path)
        canonical_json, config_hash = freeze_config(config)
        print(f"Configuration hash: {config_hash}")

        if args.output:
            args.output.write_text(canonical_json, encoding="utf-8")
            print(f"Frozen config written to: {args.output}")
        else:
            print(canonical_json)

        return 0
    except Exception as e:
        print(f"✗ Failed to freeze configuration: {e}", file=sys.stderr)
        return 1


def cmd_generate(args: argparse.Namespace) -> int:
    """Placeholder for dataset generation — not yet implemented."""
    print(
        "Dataset generation is not yet implemented.\n"
        "Current milestone: M1 — Repository, configuration, and seed foundation.\n"
        "Generation will be available after Milestone 2."
    )
    return 0


def cmd_build_fixture(args: argparse.Namespace) -> int:
    """Build the operational-only deterministic Milestone 1 fixture."""
    from satsa_generator.fixture.builder import build_fixture, parse_master_seed_hex

    seed_hex = args.seed or os.environ.get("SATSA_MASTER_SEED")
    if seed_hex is None:
        print(
            "✗ Fixture build failed: provide --seed or SATSA_MASTER_SEED.",
            file=sys.stderr,
        )
        return 1
    try:
        result = build_fixture(
            args.config_path,
            parse_master_seed_hex(seed_hex),
            output_root=args.output,
        )
        print("✓ Milestone 1 fixture built.")
        print(f"  Operational root: {result.operational_root}")
        print(f"  Tree SHA-256: {result.tree_sha256}")
        print(f"  Records: {result.record_counts}")
        print("  Ground truth: not generated")
        return 0
    except Exception as exc:
        print(f"✗ Fixture build failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the generator CLI."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "validate-config": cmd_validate_config,
        "freeze-config": cmd_freeze_config,
        "generate": cmd_generate,
        "build-fixture": cmd_build_fixture,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
