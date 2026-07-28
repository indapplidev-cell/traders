"""Minimal pool-free PostgreSQL authentication probe.

The probe parses only structured PostgreSQL protocol fields.  In particular,
it never renders the human-readable ErrorResponse message.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import socket
import struct
from dataclasses import dataclass


_PROTOCOL_VERSION_3 = 196608
_AUTHENTICATION_OK = 0
_AUTHENTICATION_CLEARTEXT_PASSWORD = 3
_AUTHENTICATION_MD5_PASSWORD = 5
_AUTHENTICATION_SASL = 10
_AUTHENTICATION_SASL_CONTINUE = 11
_AUTHENTICATION_SASL_FINAL = 12
_MAX_MESSAGE_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class PostgresAuthenticationProbe:
    connection: str
    sqlstate: str | None
    pool_disabled: bool = True
    retries: int = 0


def _pack_message(message_type: bytes, payload: bytes) -> bytes:
    return message_type + struct.pack("!I", len(payload) + 4) + payload


def _read_exact(stream: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.recv(remaining)
        if not chunk:
            raise ConnectionError()
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_message(stream: socket.socket) -> tuple[bytes, bytes]:
    message_type = _read_exact(stream, 1)
    length = struct.unpack("!I", _read_exact(stream, 4))[0]
    if length < 4 or length > _MAX_MESSAGE_BYTES:
        raise ValueError()
    return message_type, _read_exact(stream, length - 4)


def extract_error_response_sqlstate(payload: bytes) -> str | None:
    """Extract field ``C`` without decoding or returning message field ``M``."""

    offset = 0
    while offset < len(payload):
        field_type = payload[offset : offset + 1]
        offset += 1
        if field_type == b"\x00":
            break
        terminator = payload.find(b"\x00", offset)
        if terminator < 0:
            return None
        value = payload[offset:terminator]
        offset = terminator + 1
        if field_type == b"C":
            try:
                sqlstate = value.decode("ascii").upper()
            except UnicodeDecodeError:
                return None
            return sqlstate if len(sqlstate) == 5 else None
    return None


def _scram_escape_username(username: str) -> str:
    return username.replace("=", "=3D").replace(",", "=2C")


def _parse_scram_attributes(payload: bytes) -> dict[bytes, bytes]:
    attributes: dict[bytes, bytes] = {}
    for item in payload.split(b","):
        key, separator, value = item.partition(b"=")
        if separator != b"=" or len(key) != 1:
            raise ValueError()
        attributes[key] = value
    return attributes


def _scram_client_first(username: str) -> tuple[bytes, bytes]:
    nonce = base64.b64encode(os.urandom(24)).rstrip(b"=")
    bare = b"n=" + _scram_escape_username(username).encode("utf-8") + b",r=" + nonce
    return bare, b"n,," + bare


def _scram_client_final(
    *,
    password: str,
    client_first_bare: bytes,
    server_first: bytes,
) -> bytes:
    attributes = _parse_scram_attributes(server_first)
    nonce = attributes[b"r"]
    salt = base64.b64decode(attributes[b"s"], validate=True)
    iterations = int(attributes[b"i"])
    if iterations <= 0:
        raise ValueError()

    final_without_proof = b"c=biws,r=" + nonce
    auth_message = (
        client_first_bare + b"," + server_first + b"," + final_without_proof
    )
    salted_password = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    client_key = hmac.new(
        salted_password,
        b"Client Key",
        hashlib.sha256,
    ).digest()
    stored_key = hashlib.sha256(client_key).digest()
    client_signature = hmac.new(
        stored_key,
        auth_message,
        hashlib.sha256,
    ).digest()
    proof = bytes(
        left ^ right for left, right in zip(client_key, client_signature, strict=True)
    )
    return final_without_proof + b",p=" + base64.b64encode(proof)


def _md5_password(password: str, username: str, salt: bytes) -> bytes:
    inner = hashlib.md5(  # noqa: S324 - required by PostgreSQL MD5 auth protocol
        (password + username).encode("utf-8")
    ).hexdigest().encode("ascii")
    outer = hashlib.md5(  # noqa: S324 - required by PostgreSQL MD5 auth protocol
        inner + salt
    ).hexdigest().encode("ascii")
    return b"md5" + outer


def probe_postgres_authentication(
    *,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    timeout_seconds: float,
) -> PostgresAuthenticationProbe:
    """Open one direct connection and return its structured auth outcome."""

    parameters = (
        b"user\x00"
        + username.encode("utf-8")
        + b"\x00database\x00"
        + database.encode("utf-8")
        + b"\x00client_encoding\x00UTF8\x00\x00"
    )
    startup = struct.pack(
        "!II",
        len(parameters) + 8,
        _PROTOCOL_VERSION_3,
    ) + parameters

    client_first_bare: bytes | None = None
    with socket.create_connection((host, port), timeout=timeout_seconds) as stream:
        stream.settimeout(timeout_seconds)
        stream.sendall(startup)
        while True:
            message_type, payload = _read_message(stream)
            if message_type == b"E":
                return PostgresAuthenticationProbe(
                    connection="DENIED",
                    sqlstate=extract_error_response_sqlstate(payload),
                )
            if message_type == b"Z":
                return PostgresAuthenticationProbe(
                    connection="CONNECTED",
                    sqlstate=None,
                )
            if message_type != b"R" or len(payload) < 4:
                continue

            auth_code = struct.unpack("!I", payload[:4])[0]
            auth_data = payload[4:]
            if auth_code == _AUTHENTICATION_OK:
                continue
            if auth_code == _AUTHENTICATION_CLEARTEXT_PASSWORD:
                stream.sendall(
                    _pack_message(b"p", password.encode("utf-8") + b"\x00")
                )
                continue
            if auth_code == _AUTHENTICATION_MD5_PASSWORD:
                stream.sendall(
                    _pack_message(
                        b"p",
                        _md5_password(password, username, auth_data[:4]) + b"\x00",
                    )
                )
                continue
            if auth_code == _AUTHENTICATION_SASL:
                mechanisms = auth_data.rstrip(b"\x00").split(b"\x00")
                if b"SCRAM-SHA-256" not in mechanisms:
                    raise RuntimeError()
                client_first_bare, client_first = _scram_client_first(username)
                initial = (
                    b"SCRAM-SHA-256\x00"
                    + struct.pack("!I", len(client_first))
                    + client_first
                )
                stream.sendall(_pack_message(b"p", initial))
                continue
            if auth_code == _AUTHENTICATION_SASL_CONTINUE:
                if client_first_bare is None:
                    raise RuntimeError()
                stream.sendall(
                    _pack_message(
                        b"p",
                        _scram_client_final(
                            password=password,
                            client_first_bare=client_first_bare,
                            server_first=auth_data,
                        ),
                    )
                )
                continue
            if auth_code == _AUTHENTICATION_SASL_FINAL:
                continue
            raise RuntimeError()


__all__ = [
    "PostgresAuthenticationProbe",
    "extract_error_response_sqlstate",
    "probe_postgres_authentication",
]
