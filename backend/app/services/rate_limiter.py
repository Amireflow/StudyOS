"""Limitation persistante des tentatives d'authentification et d'appels coûteux."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
from threading import RLock
from uuid import uuid4
from fastapi import Request
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.errors import AppError
from app.models.tables import AuthLoginAttemptTable

DEFAULT_WINDOW_SECONDS = 300
DEFAULT_ACCOUNT_MAX_FAILURES = 10
DEFAULT_IP_MAX_FAILURES = 25
REGISTER_WINDOW_SECONDS = 3600
REGISTER_IP_MAX_ATTEMPTS = 15
MODELS_PROBE_WINDOW_SECONDS = 60
MODELS_PROBE_IP_MAX_ATTEMPTS = 20


def _hash_identifier(settings: Settings, scope: str, raw_value: str) -> str:
    salt = (settings.app_secret_key or "studyos").encode("utf-8")
    payload = f"{scope}:{raw_value.strip().lower()}".encode("utf-8")
    return hashlib.sha256(salt + b"|" + payload).hexdigest()


def _parse_ip(raw: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not raw:
        return None
    cleaned = raw.strip().strip("[]")
    try:
        return ipaddress.ip_address(cleaned)
    except ValueError:
        return None


def _is_trusted_proxy(peer_ip: str | None, settings: Settings) -> bool:
    if not peer_ip:
        return False
    parsed_peer = _parse_ip(peer_ip)
    for entry in settings.trusted_proxy_list:
        if "/" in entry and parsed_peer is not None:
            try:
                if parsed_peer in ipaddress.ip_network(entry, strict=False):
                    return True
            except ValueError:
                continue
        elif entry == peer_ip.strip():
            return True
    return False


def resolve_client_ip(request: Request | None, settings: Settings) -> str:
    """
    Extrait l'adresse IP client de manière fiable :
    ne fait confiance à X-Forwarded-For (IP la plus à droite hors proxies de confiance)
    que si la connexion directe provient d'un proxy explicitement configuré dans TRUSTED_PROXY_IPS.
    """
    if request is None or request.client is None:
        return "unknown"
    peer_ip = (request.client.host or "").strip() or "unknown"
    if not _is_trusted_proxy(peer_ip, settings):
        return peer_ip

    xff = request.headers.get("x-forwarded-for") or ""
    if not xff.strip():
        return peer_ip

    candidates = [part.strip() for part in xff.split(",") if part.strip()]
    # Remonter de droite à gauche en sautant d'éventuels proxies de confiance intermédiaires
    for raw_hop in reversed(candidates):
        if _parse_ip(raw_hop) is None:
            continue
        if not _is_trusted_proxy(raw_hop, settings):
            return raw_hop
    return peer_ip


class PersistentRateLimiter:
    """Limiteur glissant persistant en base SQLAlchemy (avec repli mémoire isolé si sans DB)."""

    def __init__(
        self,
        *,
        db: Session | None,
        settings: Settings,
        memory_attempts: list[tuple[str, str | None, str, bool, datetime]] | None = None,
        lock: RLock | None = None,
    ) -> None:
        self._db = db
        self._settings = settings
        self._mem = memory_attempts if memory_attempts is not None else []
        self._lock = lock or RLock()

    def _count_failures(
        self,
        *,
        scope: str,
        cutoff: datetime,
        account_hash: str | None = None,
        ip_hash: str | None = None,
    ) -> int:
        if self._db is not None:
            stmt = select(func.count(AuthLoginAttemptTable.id)).where(
                AuthLoginAttemptTable.scope == scope,
                AuthLoginAttemptTable.succeeded.is_(False),
                AuthLoginAttemptTable.attempted_at >= cutoff,
            )
            if account_hash is not None:
                stmt = stmt.where(AuthLoginAttemptTable.account_key_hash == account_hash)
            if ip_hash is not None:
                stmt = stmt.where(AuthLoginAttemptTable.client_ip_hash == ip_hash)
            return int(self._db.scalar(stmt) or 0)

        with self._lock:
            count = 0
            for s, a_hash, i_hash, succeeded, ts in self._mem:
                if s != scope or succeeded or ts < cutoff:
                    continue
                if account_hash is not None and a_hash != account_hash:
                    continue
                if ip_hash is not None and i_hash != ip_hash:
                    continue
                count += 1
            return count

    def assert_allowed(
        self,
        *,
        scope: str,
        account_key: str | None,
        client_ip: str,
        now_utc: datetime,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        max_account_failures: int = DEFAULT_ACCOUNT_MAX_FAILURES,
        max_ip_failures: int = DEFAULT_IP_MAX_FAILURES,
    ) -> None:
        cutoff = now_utc - timedelta(seconds=window_seconds)
        ip_hash = _hash_identifier(self._settings, f"{scope}:ip", client_ip)
        ip_failures = self._count_failures(scope=scope, cutoff=cutoff, ip_hash=ip_hash)
        if ip_failures >= max_ip_failures:
            raise AppError(
                429,
                "RATE_LIMITED",
                "Trop de tentatives depuis cette origine. Patientez quelques minutes avant de réessayer.",
            )

        if account_key:
            account_hash = _hash_identifier(self._settings, f"{scope}:acct", account_key)
            account_failures = self._count_failures(
                scope=scope,
                cutoff=cutoff,
                account_hash=account_hash,
            )
            if account_failures >= max_account_failures:
                raise AppError(
                    429,
                    "RATE_LIMITED",
                    "Trop de tentatives de connexion échouées. Patientez quelques minutes avant de réessayer.",
                )

    def record_attempt(
        self,
        *,
        scope: str,
        account_key: str | None,
        client_ip: str,
        succeeded: bool,
        now_utc: datetime,
    ) -> None:
        account_hash = (
            _hash_identifier(self._settings, f"{scope}:acct", account_key)
            if account_key
            else None
        )
        ip_hash = _hash_identifier(self._settings, f"{scope}:ip", client_ip)

        if self._db is not None:
            # Purge opportuniste des anciens enregistrements (> 24h)
            stale_cutoff = now_utc - timedelta(hours=24)
            self._db.execute(
                delete(AuthLoginAttemptTable).where(
                    AuthLoginAttemptTable.attempted_at < stale_cutoff
                )
            )
            if succeeded and account_hash is not None:
                self._db.execute(
                    delete(AuthLoginAttemptTable).where(
                        AuthLoginAttemptTable.scope == scope,
                        AuthLoginAttemptTable.account_key_hash == account_hash,
                        AuthLoginAttemptTable.succeeded.is_(False),
                    )
                )
            self._db.add(
                AuthLoginAttemptTable(
                    id=uuid4(),
                    scope=scope,
                    account_key_hash=account_hash,
                    client_ip_hash=ip_hash,
                    succeeded=succeeded,
                    attempted_at=now_utc,
                )
            )
            self._db.commit()
            return

        with self._lock:
            stale_cutoff = now_utc - timedelta(hours=24)
            self._mem[:] = [item for item in self._mem if item[4] >= stale_cutoff]
            if succeeded and account_hash is not None:
                self._mem[:] = [
                    item
                    for item in self._mem
                    if not (item[0] == scope and item[1] == account_hash and not item[3])
                ]
            self._mem.append((scope, account_hash, ip_hash, succeeded, now_utc))

    def count_all_in_window(
        self,
        *,
        scope: str,
        client_ip: str,
        now_utc: datetime,
        window_seconds: int,
    ) -> int:
        cutoff = now_utc - timedelta(seconds=window_seconds)
        ip_hash = _hash_identifier(self._settings, f"{scope}:ip", client_ip)
        if self._db is not None:
            return int(
                self._db.scalar(
                    select(func.count(AuthLoginAttemptTable.id)).where(
                        AuthLoginAttemptTable.scope == scope,
                        AuthLoginAttemptTable.client_ip_hash == ip_hash,
                        AuthLoginAttemptTable.attempted_at >= cutoff,
                    )
                )
                or 0
            )
        with self._lock:
            return sum(1 for item in self._mem if item[0] == scope and item[2] == ip_hash and item[4] >= cutoff)
