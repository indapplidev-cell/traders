from __future__ import annotations

import ast
from pathlib import Path

from app.engine_paper.production_preparation import MOBILE_SECURITY_RUNTIME_GRANTS


ROOT = Path(__file__).resolve().parents[2]


def test_mobile_auth_runtime_grants_are_exact_and_narrow():
    assert tuple((grant.table, grant.operations) for grant in MOBILE_SECURITY_RUNTIME_GRANTS) == (
        ("control_mobile_devices", ("SELECT",)),
        ("control_mobile_replay_nonces", ("INSERT",)),
    )


def test_ordinary_auth_call_graph_needs_only_registry_read_and_nonce_insert():
    source = (ROOT / "app/operator_control/mobile_security.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    verifier = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MobileRequestVerifier"
    )
    authenticate = next(
        node for node in verifier.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "authenticate"
    )
    calls = {
        node.func.attr
        for node in ast.walk(authenticate)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert {"get_device", "claim_nonce"} <= calls
    assert calls.isdisjoint({
        "register_device", "revoke_device", "rotate_device_key", "cleanup_expired"
    })


def test_runtime_binding_and_store_composition_share_proven_existing_principal_key():
    source = (ROOT / "app/operator_control/runtime.py").read_text(encoding="utf-8")
    assert "database_url = os.environ.get(RUNTIME_DATABASE_KEY)" in source
    assert "SqlAlchemyMobileSecurityStore(sessions)" in source
    assert "TRADERS_PAPER_RUNTIME_DATABASE_URL" in (
        ROOT / "app/engine_paper/production_preparation_backend.py"
    ).read_text(encoding="utf-8")
