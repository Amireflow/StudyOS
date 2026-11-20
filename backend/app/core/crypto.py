"""Chiffrement authentifié (AES-256-GCM) des clés API des fournisseurs IA."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import os
import re
from uuid import UUID
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.errors import AppError

ENCRYPTED_PREFIX = "enc:v1:"
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def _decode_raw_32byte_key(raw: str) -> bytes:
    cleaned = raw.strip()
    if len(cleaned) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in cleaned):
        decoded = bytes.fromhex(cleaned)
        if len(decoded) == 32:
            return decoded

    padded = cleaned + ("=" * ((4 - len(cleaned) % 4) % 4))
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(padded.encode("ascii"))
            if len(decoded) == 32:
                return decoded
        except Exception:
            continue

    raise AppError(
        503,
        "AI_ENCRYPTION_NOT_CONFIGURED",
        "Clé de chiffrement IA invalide : fournissez 32 octets encodés en base64 ou 64 caractères hexadécimaux.",
    )


def _parse_key_entry(entry: str, *, default_key_id: str) -> tuple[str, bytes]:
    cleaned = entry.strip()
    if ":" in cleaned:
        key_id, secret_part = cleaned.split(":", 1)
        key_id = key_id.strip()
        if not _KEY_ID_PATTERN.match(key_id):
            raise AppError(
                503,
                "AI_ENCRYPTION_NOT_CONFIGURED",
                "Identifiant de clé de chiffrement invalide.",
            )
        return key_id, _decode_raw_32byte_key(secret_part)
    return default_key_id, _decode_raw_32byte_key(cleaned)


def _build_keyring(settings: Settings) -> tuple[str, bytes, dict[str, bytes]]:
    raw_primary = (settings.ai_key_encryption_key or "").strip()
    if not raw_primary:
        raise AppError(
            503,
            "AI_ENCRYPTION_NOT_CONFIGURED",
            "Le stockage chiffré des clés API IA n’est pas configuré sur le serveur (AI_KEY_ENCRYPTION_KEY manquant).",
        )

    primary_id, primary_bytes = _parse_key_entry(raw_primary, default_key_id="k1")
    keyring: dict[str, bytes] = {primary_id: primary_bytes}

    raw_fallbacks = (settings.ai_key_encryption_fallback_keys or "").strip()
    if raw_fallbacks:
        for idx, part in enumerate(raw_fallbacks.split(","), start=2):
            item = part.strip()
            if not item:
                continue
            fb_id, fb_bytes = _parse_key_entry(item, default_key_id=f"k{idx}")
            keyring.setdefault(fb_id, fb_bytes)

    return primary_id, primary_bytes, keyring


def is_encrypted_api_key(value: str | None) -> bool:
    return bool(value and value.startswith(ENCRYPTED_PREFIX))


def mask_api_key_last4(plaintext: str | None) -> str | None:
    cleaned = (plaintext or "").strip()
    if not cleaned:
        return None
    if len(cleaned) <= 8:
        return "••••"
    return f"{cleaned[:4]}…{cleaned[-4:]}"


def extract_api_key_last4(plaintext: str | None) -> str | None:
    cleaned = (plaintext or "").strip()
    if not cleaned:
        return None
    return cleaned[-4:]


def encrypt_api_key(plaintext: str, user_id: UUID, settings: Settings) -> str:
    cleaned = (plaintext or "").strip()
    if not cleaned:
        return ""

    key_id, primary_bytes, _ = _build_keyring(settings)
    nonce = os.urandom(12)
    aad = f"studyos:ai_key:{user_id}".encode("utf-8")
    ciphertext = AESGCM(primary_bytes).encrypt(nonce, cleaned.encode("utf-8"), aad)
    payload_b64 = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{key_id}:{payload_b64}"


def decrypt_api_key(token: str | None, user_id: UUID, settings: Settings) -> str:
    cleaned = (token or "").strip()
    if not cleaned:
        return ""
    if not cleaned.startswith(ENCRYPTED_PREFIX):
        raise AppError(
            500,
            "AI_CREDENTIALS_ERROR",
            "Format de clé API chiffrée invalide ou non protégé.",
        )

    remainder = cleaned[len(ENCRYPTED_PREFIX) :]
    if ":" not in remainder:
        raise AppError(500, "AI_CREDENTIALS_ERROR", "Enveloppe de chiffrement IA invalide.")
    key_id, payload_b64 = remainder.split(":", 1)

    _, _, keyring = _build_keyring(settings)
    key_bytes = keyring.get(key_id)
    if key_bytes is None:
        raise AppError(
            503,
            "AI_ENCRYPTION_KEY_UNAVAILABLE",
            "Clé de déchiffrement introuvable pour cette configuration IA.",
        )

    try:
        raw = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        if len(raw) < 28:
            raise ValueError("Payload trop court")
        nonce, ciphertext = raw[:12], raw[12:]
        aad = f"studyos:ai_key:{user_id}".encode("utf-8")
        plaintext_bytes = AESGCM(key_bytes).decrypt(nonce, ciphertext, aad)
        return plaintext_bytes.decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
        raise AppError(
            503,
            "AI_DECRYPTION_FAILED",
            "Impossible de déchiffrer la clé API enregistrée. Veuillez la saisir à nouveau.",
        ) from exc


def migrate_legacy_plaintext_ai_keys(db: Session, settings: Settings) -> int:
    """
    Migre de manière contrôlée d'éventuelles anciennes configurations stockées en clair
    dans `profiles.preferences['_ai_provider_config']` vers `user_ai_provider_configs`.
    """
    from app.models.tables import ProfileTable, UserAiProviderConfigTable

    # Échoue proprement si la clé de chiffrement n'est pas configurée
    _build_keyring(settings)

    migrated = 0
    rows = db.scalars(select(ProfileTable)).all()
    now = datetime.now(timezone.utc)
    for prof in rows:
        prefs = dict(prof.preferences or {})
        legacy = prefs.pop("_ai_provider_config", None)
        if not isinstance(legacy, dict):
            continue

        raw_key = str(legacy.get("api_key") or "").strip()
        encrypted = (
            encrypt_api_key(raw_key, prof.id, settings)
            if raw_key and not is_encrypted_api_key(raw_key)
            else (raw_key if is_encrypted_api_key(raw_key) else None)
        )
        last4 = extract_api_key_last4(raw_key) if raw_key else None
        existing_cfg = db.scalar(
            select(UserAiProviderConfigTable).where(UserAiProviderConfigTable.user_id == prof.id)
        )
        if existing_cfg is None:
            db.add(
                UserAiProviderConfigTable(
                    user_id=prof.id,
                    provider=str(legacy.get("provider") or "local")[:30],
                    base_url=str(legacy.get("base_url") or "")[:300],
                    model=str(legacy.get("model") or "")[:160],
                    encrypted_api_key=encrypted,
                    key_version=1,
                    api_key_last4=last4,
                    created_at=now,
                    updated_at=now,
                )
            )
        elif not existing_cfg.encrypted_api_key and encrypted:
            existing_cfg.encrypted_api_key = encrypted
            existing_cfg.api_key_last4 = last4
            existing_cfg.updated_at = now

        prof.preferences = prefs
        prof.updated_at = now
        migrated += 1

    if migrated > 0:
        db.commit()
    return migrated
