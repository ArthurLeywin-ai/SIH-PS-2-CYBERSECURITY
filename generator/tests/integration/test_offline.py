from __future__ import annotations

import socket

from satsa_generator.fixture.builder import build_fixture


def test_fixture_build_does_not_require_network(
    monkeypatch, tmp_path, fixture_config_path, master_seed
):
    def blocked(*args, **kwargs):
        raise AssertionError("network access is prohibited during fixture generation")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)

    result = build_fixture(
        fixture_config_path, master_seed, output_root=tmp_path / "offline"
    )
    assert result.manifest_path.is_file()
