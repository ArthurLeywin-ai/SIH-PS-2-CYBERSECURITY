"""
Seed module — master/child seed derivation and named RNG registry.

Provides deterministic, reproducible random streams derived from a master
seed via HMAC-SHA-256. Every component gets an independent named stream,
ensuring that changes to one component (e.g., note templates) cannot
affect another (e.g., alert counts).
"""
