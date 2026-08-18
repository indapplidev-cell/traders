from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import socket
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uvicorn

from app.operator_control.app import create_paper_operator_control_app
from app.operator_control.config import (
    ControlAuthProfile,
    PaperOperatorControlConfig,
    PaperOperatorControlOperationMode,
)
from app.operator_control.mobile_security import (
    ALGORITHM,
    SCHEME,
    InMemoryMobileSecurityStore,
    MobileDevice,
    MobileRequestVerifier,
    SignedRequestEnvelope,
    SqlAlchemyMobileSecurityStore,
)
from app.operator_control.schemas import (
    PaperCanaryNormalizedState,
    PaperOperatorCanaryStatus,
    PaperOperatorControlDecision,
    PaperOperatorControlStatus,
)
from app.operator_control.service import ControlApiError


NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


class StubService:
    def status(self):
        return PaperOperatorControlStatus(
            control_api_version="1", foundation_mode="DISABLED_FOUNDATION",
            service_enabled=False, bind_scope="TEST_LOOPBACK", environment="TEST",
            mode="PAPER", control_state="DISABLED", effective_state="DISABLED",
            generation=6, control_health="HEALTHY", audit_health="PASS",
            state_audit_reconciliation="PASS", emergency_stop_available=True,
            live_allowed=False, production_mutation_enabled=False,
        )

    def canary_status(self, **_kwargs):
        return PaperOperatorCanaryStatus(
            state=PaperCanaryNormalizedState.ARMED, availability_code="AVAILABLE",
            deployment_status="TEST", current_control_generation=6,
        )

    def disable(self, request):
        if request.expected_generation != 6:
            raise ControlApiError(409, "STALE_GENERATION")
        return PaperOperatorControlDecision(
            request_id=request.request_id, operation="DISABLE", accepted=True,
            executed=True, state_before="ARMED", state_after="DISABLED",
            generation_before=6, generation_after=7,
        )

    arm_first_canary = start_first_canary = emergency_stop = clear_emergency_stop = disable


@pytest.fixture
def identity():
    key = ec.generate_private_key(ec.SECP256R1())
    spki = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    device = MobileDevice(
        device_id=str(uuid4()), public_key_spki=spki,
        public_key_fingerprint=hashlib.sha256(spki).hexdigest(), algorithm=ALGORITHM,
        key_version=1, enabled=True, created_at=NOW,
    )
    return key, device


def config():
    return PaperOperatorControlConfig(
        auth_profile=ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS,
        operation_mode=PaperOperatorControlOperationMode.DISABLED_FOUNDATION,
        environment="TEST", mobile_persistence_configured=True,
        allow_test_mobile_plaintext=True,
    )


def signed_headers(key, device, *, method="GET", path="/control/v1/status", query="", body=b"", action="STATUS", generation="", request_id="mobile-request-01", nonce=None, issued_at=None):
    nonce = nonce or base64.urlsafe_b64encode(b"0123456789abcdef").decode().rstrip("=")
    envelope = SignedRequestEnvelope(
        scheme=SCHEME, device_id=device.device_id, key_version=device.key_version,
        method=method, path=path, query=query,
        body_sha256=hashlib.sha256(body).hexdigest(),
        issued_at=int((issued_at or NOW).timestamp()), nonce=nonce,
        request_id=request_id, action=action, expected_generation=generation,
    )
    signature = key.sign(envelope.canonical_bytes(), ec.ECDSA(hashes.SHA256()))
    return {
        "X-Traders-Control-Scheme": SCHEME,
        "X-Traders-Device-Id": device.device_id,
        "X-Traders-Key-Version": str(device.key_version),
        "X-Traders-Issued-At": str(envelope.issued_at),
        "X-Traders-Nonce": nonce,
        "X-Traders-Request-Id": request_id,
        "X-Traders-Action": action,
        "X-Traders-Expected-Generation": generation,
        "X-Traders-Signature": base64.urlsafe_b64encode(signature).decode().rstrip("="),
    }


def client(identity, store=None):
    key, device = identity
    active_store = store or InMemoryMobileSecurityStore((device,))
    verifier = MobileRequestVerifier(active_store, clock=lambda: NOW)
    app = create_paper_operator_control_app(
        config=config(), service=StubService(), mobile_verifier=verifier
    )
    return TestClient(app, raise_server_exceptions=False), key, device, active_store


def test_valid_device_and_mobile_profile_rejects_bearer_and_unsigned(identity):
    api, key, device, _ = client(identity)
    assert api.get("/control/v1/status", headers=signed_headers(key, device)).status_code == 200
    assert api.get("/control/v1/status").json()["error"]["code"] == "MOBILE_AUTH_MISSING"
    response = api.get("/control/v1/status", headers={"Authorization": "Bearer operator-secret"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MOBILE_AUTH_MISSING"
    unsigned_mutation = api.post(
        "/control/v1/disable",
        json={"request_id": "mobile-request-01", "expected_generation": 6, "operator_acknowledgement": True},
    )
    assert unsigned_mutation.status_code == 401
    assert unsigned_mutation.json()["error"]["code"] == "MOBILE_AUTH_MISSING"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda h: h.__setitem__("X-Traders-Control-Scheme", "v2"), "MOBILE_AUTH_PROFILE_INVALID"),
        (lambda h: h.__setitem__("X-Traders-Key-Version", "2"), "MOBILE_KEY_VERSION_INVALID"),
        (lambda h: h.__setitem__("X-Traders-Signature", "AA"), "MOBILE_SIGNATURE_INVALID"),
        (lambda h: h.__setitem__("X-Traders-Nonce", "B" * 22), "MOBILE_SIGNATURE_INVALID"),
        (lambda h: h.__setitem__("X-Traders-Request-Id", "mobile-request-02"), "MOBILE_SIGNATURE_INVALID"),
        (lambda h: h.__setitem__("X-Traders-Action", "DISABLE"), "MOBILE_SIGNATURE_INVALID"),
    ],
)
def test_header_tamper_matrix(identity, mutation, expected):
    api, key, device, _ = client(identity)
    headers = signed_headers(key, device)
    mutation(headers)
    response = api.get("/control/v1/status", headers=headers)
    assert response.status_code in (401, 409)
    assert response.json()["error"]["code"] == expected


def test_method_path_query_and_other_device_tamper(identity):
    api, key, device, _ = client(identity)
    method_headers = signed_headers(key, device, method="POST")
    assert api.get("/control/v1/status", headers=method_headers).json()["error"]["code"] == "MOBILE_SIGNATURE_INVALID"
    path_headers = signed_headers(key, device, path="/control/v1/canary/status", action="CANARY_STATUS")
    assert api.get("/control/v1/canary/status", headers=path_headers).status_code == 200
    assert api.get("/control/v1/status", headers=path_headers).json()["error"]["code"] == "MOBILE_SIGNATURE_INVALID"
    query_headers = signed_headers(key, device, query="canary_id=one", path="/control/v1/canary/status", action="CANARY_STATUS")
    assert api.get("/control/v1/canary/status?canary_id=two", headers=query_headers).json()["error"]["code"] == "MOBILE_SIGNATURE_INVALID"
    other = dict(signed_headers(key, device))
    other["X-Traders-Device-Id"] = str(uuid4())
    assert api.get("/control/v1/status", headers=other).json()["error"]["code"] == "MOBILE_DEVICE_UNKNOWN"


def test_body_generation_action_and_replay(identity):
    api, key, device, _ = client(identity)
    body = json.dumps(
        {"request_id": "mobile-request-01", "expected_generation": 6, "operator_acknowledgement": True},
        separators=(",", ":"),
    ).encode()
    headers = signed_headers(
        key, device, method="POST", path="/control/v1/disable", body=body,
        action="DISABLE", generation="6",
    )
    assert api.post("/control/v1/disable", content=body, headers=headers).status_code == 200
    replay = api.post("/control/v1/disable", content=body, headers=headers)
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "MOBILE_REPLAY_DETECTED"

    same_request_new_nonce = signed_headers(
        key, device, method="POST", path="/control/v1/disable", body=body,
        action="DISABLE", generation="6", nonce="E" * 22,
    )
    assert api.post(
        "/control/v1/disable", content=body, headers=same_request_new_nonce
    ).status_code == 200
    different_request_body = body.replace(b"mobile-request-01", b"mobile-request-02")
    same_nonce_new_request = signed_headers(
        key, device, method="POST", path="/control/v1/disable",
        body=different_request_body, action="DISABLE", generation="6",
        request_id="mobile-request-02",
    )
    assert api.post(
        "/control/v1/disable", content=different_request_body,
        headers=same_nonce_new_request,
    ).json()["error"]["code"] == "MOBILE_REPLAY_DETECTED"

    changed_body = body.replace(b"true", b"false")
    fresh_headers = signed_headers(
        key, device, method="POST", path="/control/v1/disable", body=body,
        action="DISABLE", generation="6", nonce="C" * 22,
    )
    assert api.post("/control/v1/disable", content=changed_body, headers=fresh_headers).json()["error"]["code"] == "MOBILE_SIGNATURE_INVALID"
    bad_generation = dict(signed_headers(
        key, device, method="POST", path="/control/v1/disable", body=body,
        action="DISABLE", generation="6", nonce="D" * 22,
    ))
    bad_generation["X-Traders-Expected-Generation"] = "7"
    assert api.post("/control/v1/disable", content=body, headers=bad_generation).json()["error"]["code"] == "MOBILE_SIGNATURE_INVALID"

    wrong_body = body.replace(b'"expected_generation":6', b'"expected_generation":7')
    wrong_headers = signed_headers(
        key, device, method="POST", path="/control/v1/disable", body=wrong_body,
        action="DISABLE", generation="7", nonce="F" * 22,
    )
    wrong = api.post("/control/v1/disable", content=wrong_body, headers=wrong_headers)
    assert wrong.status_code == 409
    assert wrong.json()["error"]["code"] == "MOBILE_GENERATION_MISMATCH"


def test_expired_future_revoked_and_unsupported_algorithm(identity):
    key, device = identity
    api, _, _, _ = client(identity)
    expired = signed_headers(key, device, issued_at=datetime(2026, 8, 17, 11, 57, tzinfo=timezone.utc))
    assert api.get("/control/v1/status", headers=expired).json()["error"]["code"] == "MOBILE_REQUEST_EXPIRED"
    future = signed_headers(key, device, issued_at=datetime(2026, 8, 17, 12, 1, tzinfo=timezone.utc))
    assert api.get("/control/v1/status", headers=future).json()["error"]["code"] == "MOBILE_REQUEST_FUTURE_SKEW"
    revoked = replace(device, enabled=False, revoked_at=NOW)
    revoked_api, _, _, _ = client(identity, InMemoryMobileSecurityStore((revoked,)))
    assert revoked_api.get("/control/v1/status", headers=signed_headers(key, device)).json()["error"]["code"] == "MOBILE_DEVICE_REVOKED"
    unsupported = replace(device, algorithm="OTHER")
    unsupported_api, _, _, _ = client(identity, InMemoryMobileSecurityStore((unsupported,)))
    assert unsupported_api.get("/control/v1/status", headers=signed_headers(key, device)).json()["error"]["code"] == "MOBILE_ALGORITHM_UNSUPPORTED"


def test_freshness_boundaries_are_exact(identity):
    api, key, device, _ = client(identity)
    oldest = signed_headers(key, device, issued_at=NOW - timedelta(seconds=120))
    assert api.get("/control/v1/status", headers=oldest).status_code == 200
    too_old = signed_headers(key, device, issued_at=NOW - timedelta(seconds=121))
    assert api.get("/control/v1/status", headers=too_old).json()["error"]["code"] == "MOBILE_REQUEST_EXPIRED"
    future_edge = signed_headers(key, device, issued_at=NOW + timedelta(seconds=30))
    assert api.get("/control/v1/status", headers=future_edge).status_code == 200
    too_future = signed_headers(key, device, issued_at=NOW + timedelta(seconds=31))
    assert api.get("/control/v1/status", headers=too_future).json()["error"]["code"] == "MOBILE_REQUEST_FUTURE_SKEW"


def test_concurrent_nonce_claim_has_one_winner(identity):
    _, device = identity
    store = InMemoryMobileSecurityStore((device,))
    values = dict(device_id=device.device_id, nonce="A" * 22, issued_at=NOW, expires_at=NOW, request_id="request01", action="STOP", accepted_at=NOW)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.claim_nonce(**values), range(20)))
    assert results.count(True) == 1
    assert results.count(False) == 19


def test_durable_nonce_survives_store_restart(tmp_path: Path, identity):
    _, device = identity
    engine = create_engine(f"sqlite:///{tmp_path / 'replay.sqlite'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE control_mobile_devices (device_id VARCHAR(36) PRIMARY KEY, public_key_spki BLOB NOT NULL, public_key_fingerprint VARCHAR(64) NOT NULL, algorithm VARCHAR(32) NOT NULL, key_version INTEGER NOT NULL, enabled BOOLEAN NOT NULL, label VARCHAR(128), created_at DATETIME NOT NULL, revoked_at DATETIME)"))
        connection.execute(text("CREATE TABLE control_mobile_replay_nonces (device_id VARCHAR(36) NOT NULL, nonce VARCHAR(128) NOT NULL, issued_at DATETIME NOT NULL, expires_at DATETIME NOT NULL, request_id VARCHAR(128) NOT NULL, action VARCHAR(48), accepted_at DATETIME NOT NULL, PRIMARY KEY (device_id, nonce), FOREIGN KEY(device_id) REFERENCES control_mobile_devices(device_id))"))
        connection.execute(text("INSERT INTO control_mobile_devices VALUES (:id,:key,:fp,:alg,1,1,NULL,:created,NULL)"), {"id": device.device_id, "key": device.public_key_spki, "fp": device.public_key_fingerprint, "alg": device.algorithm, "created": NOW})
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    values = dict(device_id=device.device_id, nonce="A" * 22, issued_at=NOW, expires_at=NOW, request_id="request01", action="STOP", accepted_at=NOW)
    assert SqlAlchemyMobileSecurityStore(sessions).claim_nonce(**values)
    engine.dispose()
    restarted = create_engine(f"sqlite:///{tmp_path / 'replay.sqlite'}")
    assert not SqlAlchemyMobileSecurityStore(sessionmaker(bind=restarted)).claim_nonce(**values)


def test_per_device_revocation_and_key_rotation_do_not_touch_global_secret(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'devices.sqlite'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE control_mobile_devices (device_id VARCHAR(36) PRIMARY KEY, public_key_spki BLOB NOT NULL, public_key_fingerprint VARCHAR(64) NOT NULL, algorithm VARCHAR(32) NOT NULL, key_version INTEGER NOT NULL, enabled BOOLEAN NOT NULL, label VARCHAR(128), created_at DATETIME NOT NULL, revoked_at DATETIME)"))
    store = SqlAlchemyMobileSecurityStore(sessionmaker(bind=engine, expire_on_commit=False))
    device_id = str(uuid4())
    first_key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    second_key = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    registered = store.register_device(
        device_id=device_id, public_key_spki=first_key, created_at=NOW, label="isolated-test"
    )
    assert registered.enabled and registered.key_version == 1
    store.revoke_device(device_id, revoked_at=NOW)
    assert not store.get_device(device_id).enabled
    rotated = store.rotate_device_key(
        device_id=device_id, public_key_spki=second_key, new_key_version=2
    )
    assert rotated.enabled and rotated.revoked_at is None and rotated.key_version == 2
    assert rotated.public_key_spki == second_key
    with pytest.raises(ValueError, match="MOBILE_KEY_VERSION_INVALID"):
        store.rotate_device_key(
            device_id=device_id, public_key_spki=first_key, new_key_version=4
        )


def test_ephemeral_https_instance_uses_normal_certificate_and_ip_validation(tmp_path: Path, identity):
    key, device = identity
    tls_key = ec.generate_private_key(ec.SECP256R1())
    tls_now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(tls_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(tls_now - timedelta(minutes=1))
        .not_valid_after(tls_now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(tls_key, hashes.SHA256())
    )
    cert_path = tmp_path / "test-control-cert.pem"
    key_path = tmp_path / "test-control-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(tls_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    tls_config = PaperOperatorControlConfig(
        auth_profile=ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS,
        operation_mode=PaperOperatorControlOperationMode.DISABLED_FOUNDATION,
        environment="TEST",
        bind_host="127.0.0.1",
        tls_enabled=True,
        tls_certificate_path=cert_path,
        tls_private_key_path=key_path,
        tls_server_identity="127.0.0.1",
        mobile_persistence_configured=True,
    )
    app = create_paper_operator_control_app(
        config=tls_config,
        service=StubService(),
        mobile_verifier=MobileRequestVerifier(
            InMemoryMobileSecurityStore((device,)), clock=lambda: NOW
        ),
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        ssl_certfile=str(cert_path),
        ssl_keyfile=str(key_path),
        lifespan="off",
        log_level="error",
    ))
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [listener]}, daemon=True
    )
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.02)
    try:
        headers = signed_headers(key, device)
        trust = ssl.create_default_context(cafile=str(cert_path))
        response = httpx.get(
            f"https://127.0.0.1:{port}/control/v1/status",
            headers=headers,
            verify=trust,
            timeout=5,
        )
        assert response.status_code == 200
        with pytest.raises(httpx.TransportError):
            httpx.get(
                f"https://localhost:{port}/control/v1/status",
                headers=headers,
                verify=trust,
                timeout=5,
            )
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
