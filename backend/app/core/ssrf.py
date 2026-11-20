"""Protection SSRF et client HTTP sortant sécurisé pour Amireflow Study OS."""

from __future__ import annotations

import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlparse
import httpx
from app.core.config import Settings
from app.core.errors import AppError

_FORBIDDEN_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}
_FORBIDDEN_SUFFIXES = (".local", ".internal", ".localhost", ".arpa")
_CGNAT_NETWORK = ipaddress.IPv4Network("100.64.0.0/10")
_MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")

MAX_AI_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 Mio
MAX_GITHUB_RESPONSE_BYTES = 512 * 1024  # 512 Kio


def _is_forbidden_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip_obj, ipaddress.IPv6Address):
        mapped = ip_obj.ipv4_mapped
        if mapped is not None:
            return _is_forbidden_ip(mapped)
        sixtofour = ip_obj.sixtofour
        if sixtofour is not None and _is_forbidden_ip(sixtofour):
            return True
    else:
        if ip_obj in _CGNAT_NETWORK:
            return True

    return bool(
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
        or not ip_obj.is_global
    )


def _check_literal_ip_or_hostname(
    hostname: str,
    *,
    is_local_dev_http: bool,
) -> None:
    lowered = hostname.lower().rstrip(".")
    if is_local_dev_http and lowered in ("localhost", "127.0.0.1"):
        return

    if lowered in _FORBIDDEN_HOSTNAMES or any(lowered.endswith(sfx) for sfx in _FORBIDDEN_SUFFIXES):
        raise AppError(
            400,
            "SSRF_BLOCKED",
            "Destination réseau interne ou réservée interdite.",
        )

    # Gestion d'adresses IP littérales (décimales, IPv6 entre crochets, IPv4-mapped)
    candidate = lowered[1:-1] if lowered.startswith("[") and lowered.endswith("]") else lowered
    try:
        ip_obj = ipaddress.ip_address(candidate)
    except ValueError:
        ip_obj = None

    if ip_obj is not None and _is_forbidden_ip(ip_obj):
        raise AppError(
            400,
            "SSRF_BLOCKED",
            "Les adresses IP privées, locales, loopback ou de métadonnées sont interdites.",
        )


def _resolve_and_verify_dns(
    hostname: str,
    port: int,
    *,
    is_local_dev_http: bool,
) -> None:
    if is_local_dev_http and hostname.lower() in ("localhost", "127.0.0.1"):
        return

    try:
        addr_infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "Impossible de résoudre le nom d’hôte de destination.",
        ) from exc

    if not addr_infos:
        raise AppError(400, "VALIDATION_ERROR", "Aucune adresse réseau résolue pour cette URL.")

    for _family, _socktype, _proto, _canonname, sockaddr in addr_infos:
        raw_ip = str(sockaddr[0]).split("%", 1)[0]
        try:
            ip_obj = ipaddress.ip_address(raw_ip)
        except ValueError as exc:
            raise AppError(400, "SSRF_BLOCKED", "Adresse IP résolue invalide.") from exc
        if _is_forbidden_ip(ip_obj):
            raise AppError(
                400,
                "SSRF_BLOCKED",
                "L’URL résout vers une adresse IP interne, privée ou réservée.",
            )


def validate_outbound_url(
    raw_url: str,
    *,
    settings: Settings | None = None,
    allow_http_local: bool = True,
    allowed_hosts: set[str] | None = None,
    verify_dns: bool = True,
) -> str:
    """
    Valide strictement une URL sortante contre les risques SSRF :
    - HTTPS obligatoire par défaut
    - Rejet identifiants, query/fragment, IP privées/loopback/link-local/réservées/cloud metadata
    - Vérification des résultats DNS
    - Exception HTTP localhost uniquement explicite en environnement local
    """
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise AppError(400, "VALIDATION_ERROR", "L’URL de destination est vide.")

    parsed = urlparse(cleaned)
    if parsed.username or parsed.password:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "L’URL ne doit pas contenir d’identifiants intégrés.",
        )
    if parsed.query or parsed.fragment:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "L’URL de base ne doit pas contenir de paramètres ou de fragments.",
        )

    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "L’URL doit contenir un nom d’hôte valide.",
        )

    if allowed_hosts is not None and hostname not in allowed_hosts:
        raise AppError(
            400,
            "SSRF_BLOCKED",
            "Hôte non autorisé pour ce type de vérification externe.",
        )

    is_local_dev_http = bool(
        allow_http_local
        and settings is not None
        and settings.app_env.strip().lower() == "local"
        and settings.allow_insecure_local_ai_url
        and scheme == "http"
        and hostname in ("localhost", "127.0.0.1")
    )

    if scheme != "https" and not is_local_dev_http:
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "L’URL de destination doit obligatoirement utiliser HTTPS.",
        )

    port = parsed.port
    if scheme == "https" and port is not None and port != 443:
        raise AppError(
            400,
            "SSRF_BLOCKED",
            "Seul le port HTTPS standard (443) est autorisé.",
        )

    _check_literal_ip_or_hostname(hostname, is_local_dev_http=is_local_dev_http)
    if verify_dns:
        _resolve_and_verify_dns(
            hostname,
            port or (80 if scheme == "http" else 443),
            is_local_dev_http=is_local_dev_http,
        )

    return cleaned.rstrip("/")


def validate_model_identifier(model: str) -> str:
    cleaned = (model or "").strip()
    if not cleaned or ".." in cleaned or not _MODEL_ID_PATTERN.match(cleaned):
        raise AppError(
            400,
            "VALIDATION_ERROR",
            "Identifiant de modèle IA invalide.",
        )
    return cleaned


def _enforce_response_bounds(response: httpx.Response, *, max_bytes: int) -> None:
    if response.status_code in (301, 302, 303, 307, 308):
        raise AppError(
            502,
            "SSRF_BLOCKED",
            "Redirection HTTP refusée par sécurité lors de la requête sortante.",
        )
    raw_len = response.headers.get("content-length")
    if raw_len and raw_len.strip().isdigit() and int(raw_len.strip()) > max_bytes:
        raise AppError(
            502,
            "UPSTREAM_RESPONSE_TOO_LARGE",
            "La réponse du service externe dépasse la taille maximale autorisée.",
        )
    if len(response.content) > max_bytes:
        raise AppError(
            502,
            "UPSTREAM_RESPONSE_TOO_LARGE",
            "La réponse du service externe dépasse la taille maximale autorisée.",
        )


def safe_http_request(
    method: str,
    url: str,
    *,
    settings: Settings | None = None,
    allow_http_local: bool = True,
    allowed_hosts: set[str] | None = None,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout_seconds: float = 20.0,
    max_bytes: int = MAX_AI_RESPONSE_BYTES,
) -> httpx.Response:
    """
    Exécute une requête HTTP sortante sécurisée :
    - Validation SSRF de la base URL (avec résolution DNS)
    - Redirections désactivées (follow_redirects=False) + rejet des statuts 3xx
    - Variables proxy système ignorées (trust_env=False)
    - Délais d'attente bornés et plafond strict de taille de réponse
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    validate_outbound_url(
        base_url,
        settings=settings,
        allow_http_local=allow_http_local,
        allowed_hosts=allowed_hosts,
        verify_dns=True,
    )

    connect_timeout = min(5.0, max(1.0, float(timeout_seconds)))
    timeout = httpx.Timeout(timeout=float(timeout_seconds), connect=connect_timeout)

    method_upper = method.strip().upper()
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        if method_upper == "GET":
            response = client.get(url, headers=headers)
        elif method_upper == "POST":
            response = client.post(url, headers=headers, json=json_body)
        else:
            response = client.request(method_upper, url, headers=headers, json=json_body)

    _enforce_response_bounds(response, max_bytes=max_bytes)
    return response
