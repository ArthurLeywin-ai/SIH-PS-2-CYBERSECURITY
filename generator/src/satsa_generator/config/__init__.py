"""
Configuration module — load, validate, resolve, freeze, and hash configuration.

This module owns the typed configuration models and the freeze/hash pipeline.
It validates references, version compatibility, and enforces the prohibition
on detector-threshold keys.
"""
