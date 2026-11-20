"""Inspection contrôlée et SSRF-safe de dépôts / ressources GitHub pour les preuves de compétences."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlparse
import httpx
from app.core.config import Settings
from app.core.errors import AppError
from app.core.ssrf import MAX_GITHUB_RESPONSE_BYTES, safe_http_request
from app.schemas.common import EvidenceVerificationStatus

_OWNER_OR_REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_SAFE_SUBPATH_PATTERN = re.compile(r"^[A-Za-z0-9._/@+-]{1,300}$")


@dataclass(frozen=True)
class ParsedGitHubTarget:
    owner: str
    repo: str
    kind: str  # "repo" | "pull" | "tree" | "blob" | "commit"
    ref: str | None = None
    path: str | None = None
    pull_number: int | None = None


@dataclass(frozen=True)
class GitHubInspectionResult:
    status: EvidenceVerificationStatus
    verified: bool
    note: str
    metadata: dict[str, Any]
    inspected_at: datetime


def parse_github_url(raw_url: str | None) -> ParsedGitHubTarget | None:
    if not raw_url or not raw_url.strip():
        return None
    parsed = urlparse(raw_url.strip())
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() != "github.com":
        return None
    if parsed.port is not None and parsed.port != 443:
        return None

    segments = [seg for seg in parsed.path.split("/") if seg]
    if len(segments) < 2:
        return None

    owner = segments[0]
    repo = segments[1].removesuffix(".git")
    if (
        not _OWNER_OR_REPO_PATTERN.match(owner)
        or not _OWNER_OR_REPO_PATTERN.match(repo)
        or owner in (".", "..")
        or repo in (".", "..")
    ):
        return None

    if len(segments) == 2:
        return ParsedGitHubTarget(owner=owner, repo=repo, kind="repo")

    action = segments[2]
    if action == "pull" and len(segments) >= 4 and segments[3].isdigit():
        return ParsedGitHubTarget(
            owner=owner,
            repo=repo,
            kind="pull",
            pull_number=int(segments[3]),
        )
    if action in ("tree", "blob") and len(segments) >= 4:
        ref = segments[3]
        subpath = "/".join(segments[4:]) if len(segments) > 4 else None
        if not _SAFE_SUBPATH_PATTERN.match(ref) or (
            subpath is not None and (not _SAFE_SUBPATH_PATTERN.match(subpath) or ".." in subpath)
        ):
            return None
        return ParsedGitHubTarget(
            owner=owner,
            repo=repo,
            kind=action,
            ref=ref,
            path=subpath,
        )
    if action == "commit" and len(segments) >= 4 and re.match(r"^[0-9a-fA-F]{7,40}$", segments[3]):
        return ParsedGitHubTarget(owner=owner, repo=repo, kind="commit", ref=segments[3])

    return ParsedGitHubTarget(owner=owner, repo=repo, kind="repo")


def inspect_github_evidence(
    reference_url: str | None,
    *,
    expected_files: list[str] | None = None,
    settings: Settings | None = None,
    timeout_seconds: float = 8.0,
) -> GitHubInspectionResult:
    """
    Vérifie une URL GitHub via l'API REST officielle (`api.github.com`) sous contrôle SSRF strict :
    - Ne prétend jamais avoir inspecté un dépôt inaccessible, privé ou non consulté.
    - Retourne `verified` ou `inspected` uniquement lorsque les métadonnées réelles sont confirmées.
    """
    now = datetime.now(timezone.utc)
    cleaned = (reference_url or "").strip()
    if not cleaned:
        return GitHubInspectionResult(
            status=EvidenceVerificationStatus.declared,
            verified=False,
            note="Aucune URL externe fournie.",
            metadata={"checked": False},
            inspected_at=now,
        )

    parsed = urlparse(cleaned)
    if (parsed.hostname or "").lower() != "github.com":
        return GitHubInspectionResult(
            status=EvidenceVerificationStatus.declared,
            verified=False,
            note=(
                "URL externe hors GitHub non inspectée automatiquement par le serveur ; "
                "l'évaluation repose sur la production et la revue."
            ),
            metadata={"checked": False, "host": (parsed.hostname or "").lower()},
            inspected_at=now,
        )

    target = parse_github_url(cleaned)
    if target is None:
        return GitHubInspectionResult(
            status=EvidenceVerificationStatus.unreachable,
            verified=False,
            note="Structure d’URL GitHub invalide (attendu : https://github.com/<utilisateur>/<depot>).",
            metadata={"checked": True, "valid_github_url": False},
            inspected_at=now,
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AmireflowStudyOS/1.0",
    }

    try:
        repo_res = safe_http_request(
            "GET",
            f"https://api.github.com/repos/{target.owner}/{target.repo}",
            settings=settings,
            allow_http_local=False,
            allowed_hosts={"api.github.com"},
            headers=headers,
            timeout_seconds=timeout_seconds,
            max_bytes=MAX_GITHUB_RESPONSE_BYTES,
        )
        if repo_res.status_code in (404, 403, 401):
            return GitHubInspectionResult(
                status=EvidenceVerificationStatus.unreachable,
                verified=False,
                note=(
                    f"Dépôt GitHub inaccessible ({repo_res.status_code}) : "
                    "introuvable, privé ou quota API GitHub atteint."
                ),
                metadata={
                    "checked": True,
                    "owner": target.owner,
                    "repo": target.repo,
                    "http_status": repo_res.status_code,
                },
                inspected_at=now,
            )
        repo_res.raise_for_status()
        repo_data = repo_res.json()

        default_branch = str(repo_data.get("default_branch") or "main")
        is_private = bool(repo_data.get("private", False))
        metadata: dict[str, Any] = {
            "checked": True,
            "owner": target.owner,
            "repo": target.repo,
            "full_name": repo_data.get("full_name"),
            "default_branch": default_branch,
            "private": is_private,
            "language": repo_data.get("language"),
            "target_kind": target.kind,
        }

        if target.kind == "pull" and target.pull_number is not None:
            pr_res = safe_http_request(
                "GET",
                f"https://api.github.com/repos/{target.owner}/{target.repo}/pulls/{target.pull_number}",
                settings=settings,
                allow_http_local=False,
                allowed_hosts={"api.github.com"},
                headers=headers,
                timeout_seconds=timeout_seconds,
                max_bytes=MAX_GITHUB_RESPONSE_BYTES,
            )
            if pr_res.status_code >= 400:
                return GitHubInspectionResult(
                    status=EvidenceVerificationStatus.unreachable,
                    verified=False,
                    note=f"Pull Request #{target.pull_number} inaccessible (HTTP {pr_res.status_code}).",
                    metadata={**metadata, "pull_http_status": pr_res.status_code},
                    inspected_at=now,
                )
            pr_data = pr_res.json()
            metadata["pull_number"] = target.pull_number
            metadata["pull_state"] = pr_data.get("state")
            metadata["pull_merged"] = bool(pr_data.get("merged", False))

        missing_files: list[str] = []
        found_files: list[str] = []
        paths_to_check: list[str] = []
        if target.path:
            paths_to_check.append(target.path)
        for item in expected_files or []:
            clean_item = item.strip().lstrip("/")
            if clean_item and ".." not in clean_item and _SAFE_SUBPATH_PATTERN.match(clean_item):
                if clean_item not in paths_to_check:
                    paths_to_check.append(clean_item)

        if paths_to_check:
            ref_param = target.ref or default_branch
            for check_path in paths_to_check[:8]:
                c_res = safe_http_request(
                    "GET",
                    f"https://api.github.com/repos/{target.owner}/{target.repo}/contents/{check_path}?ref={ref_param}",
                    settings=settings,
                    allow_http_local=False,
                    allowed_hosts={"api.github.com"},
                    headers=headers,
                    timeout_seconds=timeout_seconds,
                    max_bytes=MAX_GITHUB_RESPONSE_BYTES,
                )
                if c_res.status_code == 200:
                    found_files.append(check_path)
                else:
                    missing_files.append(check_path)

            metadata["found_files"] = found_files
            metadata["missing_files"] = missing_files
            if missing_files:
                return GitHubInspectionResult(
                    status=EvidenceVerificationStatus.inspected,
                    verified=False,
                    note=(
                        "Dépôt consulté mais fichiers/ressources attendus absents ou inaccessibles : "
                        + ", ".join(missing_files)
                    ),
                    metadata=metadata,
                    inspected_at=now,
                )
            return GitHubInspectionResult(
                status=EvidenceVerificationStatus.verified,
                verified=True,
                note=(
                    f"Dépôt GitHub {target.owner}/{target.repo} et fichier(s) vérifié(s) : "
                    + ", ".join(found_files)
                ),
                metadata=metadata,
                inspected_at=now,
            )

        # Contrôle minimal de contenu racine du dépôt (évite qu'un dépôt vide soit déclaré vérifié)
        root_res = safe_http_request(
            "GET",
            f"https://api.github.com/repos/{target.owner}/{target.repo}/contents?ref={default_branch}",
            settings=settings,
            allow_http_local=False,
            allowed_hosts={"api.github.com"},
            headers=headers,
            timeout_seconds=timeout_seconds,
            max_bytes=MAX_GITHUB_RESPONSE_BYTES,
        )
        root_entries = root_res.json() if root_res.status_code == 200 else []
        root_count = len(root_entries) if isinstance(root_entries, list) else 0
        metadata["root_entries_count"] = root_count
        if root_count == 0:
            return GitHubInspectionResult(
                status=EvidenceVerificationStatus.inspected,
                verified=False,
                note=f"Dépôt GitHub {target.owner}/{target.repo} accessible mais vide.",
                metadata=metadata,
                inspected_at=now,
            )

        return GitHubInspectionResult(
            status=EvidenceVerificationStatus.verified,
            verified=True,
            note=f"Dépôt GitHub {target.owner}/{target.repo} inspecté ({root_count} élément(s) racine).",
            metadata=metadata,
            inspected_at=now,
        )
    except AppError as exc:
        return GitHubInspectionResult(
            status=EvidenceVerificationStatus.unreachable,
            verified=False,
            note=f"Inspection GitHub bloquée ou impossible : {exc.message}",
            metadata={"checked": True, "error_code": exc.code},
            inspected_at=now,
        )
    except (httpx.HTTPError, ValueError) as exc:
        return GitHubInspectionResult(
            status=EvidenceVerificationStatus.unreachable,
            verified=False,
            note="Impossible de joindre l’API GitHub pour inspecter cette référence.",
            metadata={"checked": True, "error": type(exc).__name__},
            inspected_at=now,
        )
