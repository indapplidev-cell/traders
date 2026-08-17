from pathlib import Path

import pytest

from app.operator_control.app import create_paper_operator_control_app
from app.operator_control.config import (
    ControlAuthProfile,
    PaperOperatorControlConfig,
    PaperOperatorControlOperationMode,
)
from app.operator_control.runtime import mobile_runtime_config_from_environment


def test_operator_profile_remains_loopback_bearer_default():
    value = PaperOperatorControlConfig.production_paper()
    assert value.auth_profile is ControlAuthProfile.OPERATOR_LOOPBACK_BEARER
    assert value.bind_host == "127.0.0.1"
    assert not value.tls_enabled


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"tls_enabled": True, "tls_certificate_path": Path("cert.pem")},
        {"tls_enabled": True, "tls_private_key_path": Path("key.pem")},
        {"tls_enabled": True, "tls_certificate_path": Path("cert.pem"), "tls_private_key_path": Path("key.pem")},
        {"mobile_persistence_configured": False, "tls_enabled": True, "tls_certificate_path": Path("cert.pem"), "tls_private_key_path": Path("key.pem"), "tls_server_identity": "control.test"},
    ],
)
def test_mobile_profile_missing_tls_or_persistence_fails_closed(changes):
    values = dict(
        enabled=True,
        operation_mode=PaperOperatorControlOperationMode.PRODUCTION_PAPER,
        auth_profile=ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS,
        bind_host="192.168.1.100",
        mobile_persistence_configured=True,
    )
    values.update(changes)
    with pytest.raises(ValueError):
        PaperOperatorControlConfig(**values)


def test_plaintext_override_is_test_only():
    with pytest.raises(ValueError, match="MOBILE_TLS_REQUIRED"):
        PaperOperatorControlConfig(
            auth_profile=ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS,
            bind_host="192.168.1.100", mobile_persistence_configured=True,
            allow_test_mobile_plaintext=True,
        )


def test_production_mobile_profile_rejects_loopback_bind():
    with pytest.raises(ValueError, match="CONTROL_EXTERNAL_BIND_DENIED"):
        PaperOperatorControlConfig.mobile_device_signed_tls(
            bind_host="127.0.0.1",
            tls_certificate_path=Path("cert.pem"),
            tls_private_key_path=Path("key.pem"),
            tls_server_identity="127.0.0.1",
        )


def test_mobile_app_requires_verifier_even_when_tls_config_is_valid():
    config = PaperOperatorControlConfig.mobile_device_signed_tls(
        bind_host="192.168.1.100", tls_certificate_path=Path("cert.pem"),
        tls_private_key_path=Path("key.pem"), tls_server_identity="control.test",
    )
    with pytest.raises(ValueError, match="CONTROL_MOBILE_PERSISTENCE_REQUIRED"):
        create_paper_operator_control_app(config=config)


def test_runtime_environment_requires_real_tls_files(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADERS_CONTROL_MOBILE_BIND_HOST", "192.168.1.100")
    monkeypatch.setenv("TRADERS_CONTROL_MOBILE_TLS_CERTIFICATE", str(tmp_path / "missing.crt"))
    monkeypatch.setenv("TRADERS_CONTROL_MOBILE_TLS_PRIVATE_KEY", str(tmp_path / "missing.key"))
    monkeypatch.setenv("TRADERS_CONTROL_MOBILE_TLS_SERVER_IDENTITY", "control.test")
    with pytest.raises(RuntimeError, match="MOBILE_TLS_REQUIRED"):
        mobile_runtime_config_from_environment()
