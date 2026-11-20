"""Architecture de vérification isolée des livrables de code (sans exécution arbitraire sur l'hôte).

Ce module garantit qu'aucun code soumis par un utilisateur n'est exécuté directement
sur le serveur applicatif (FastAPI/Render). Il réalise une vérification statique
profonde (AST Python + contrats de contrôle de flux, détection de fonctions vides/stubs,
vérification de tests/assertions et détection de primitives dangereuses) et expose
une interface dédiée permettant de brancher ultérieurement un bac à sable conteneurisé.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import re


_DANGEROUS_CALL_PATTERNS: tuple[str, ...] = (
    "os.system",
    "subprocess.popen",
    "subprocess.run",
    "subprocess.call",
    "__import__",
    "eval(",
    "exec(",
    "shutil.rmtree",
)

_TEST_ASSERTION_MARKERS: tuple[str, ...] = (
    "assert ",
    "assert(",
    "pytest",
    "unittest",
    "expect(",
    "toequal(",
    "tobe(",
    "test_",
    "describe(",
    "it(",
    "check (",
    "constraint ",
)

_EDGE_CASE_MARKERS: tuple[str, ...] = (
    "raise ",
    "try:",
    "except ",
    "if not ",
    "is none",
    "valueerror",
    "typeerror",
    "throw ",
    "catch",
    "coalesce(",
    "nullif(",
    "if len(",
    "== 0",
    "<= 0",
    "not found",
    "404",
    "400",
    "422",
)


@dataclass
class SandboxVerificationReport:
    execution_mode: str = "static_isolated_ast"
    language: str = "unknown"
    syntax_valid: bool = False
    is_stub_only: bool = False
    has_real_implementation: bool = False
    has_edge_case_handling: bool = False
    has_tests_or_assertions: bool = False
    dangerous_constructs: list[str] = field(default_factory=list)
    function_count: int = 0
    non_stub_function_count: int = 0
    class_count: int = 0
    control_flow_nodes: int = 0
    quality_score: int = 0
    findings: list[str] = field(default_factory=list)


def _is_docstring_expr(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_stub_stmt(node: ast.stmt) -> bool:
    if isinstance(node, ast.Pass):
        return True
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        if node.value.value is Ellipsis or isinstance(node.value.value, str):
            return True
    if isinstance(node, ast.Return):
        if node.value is None:
            return True
        if isinstance(node.value, ast.Constant) and node.value.value in (None, "", 0, False):
            return True
    if isinstance(node, ast.Raise):
        exc = node.exc
        if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
            return True
        if (
            isinstance(exc, ast.Call)
            and isinstance(exc.func, ast.Name)
            and exc.func.id == "NotImplementedError"
        ):
            return True
    return False


def _is_stub_function(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    meaningful_body = [stmt for stmt in func_node.body if not _is_docstring_expr(stmt)]
    if not meaningful_body:
        return True
    return all(_is_stub_stmt(stmt) for stmt in meaningful_body)


def verify_code_deliverable_safely(code: str, *, language_hint: str = "") -> SandboxVerificationReport:
    """Analyse de manière isolée et sécurisée un bloc de code sans jamais l'exécuter sur l'hôte."""
    cleaned = (code or "").strip()
    if not cleaned:
        return SandboxVerificationReport(
            language=language_hint or "unknown",
            findings=["Aucun code exécutable ou livrable technique fourni."],
        )

    lowered = cleaned.lower()
    dangerous = [pat for pat in _DANGEROUS_CALL_PATTERNS if pat in lowered]
    has_tests = any(marker in lowered for marker in _TEST_ASSERTION_MARKERS)
    has_edge_cases = any(marker in lowered for marker in _EDGE_CASE_MARKERS)

    # 1. Tentative d'analyse AST Python stricte
    looks_python = (
        language_hint.lower() in ("py", "python")
        or bool(re.search(r"(?m)^\s*(?:def |async def |class |import |from .+ import )", cleaned))
    )
    if looks_python:
        try:
            tree = ast.parse(cleaned)
        except SyntaxError as exc:
            return SandboxVerificationReport(
                language="python",
                syntax_valid=False,
                dangerous_constructs=dangerous,
                findings=[f"Erreur de syntaxe Python (ligne {exc.lineno}) : {exc.msg}."],
            )

        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        non_stub_functions = [f for f in functions if not _is_stub_function(f)]
        control_flow = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.Match))
        ]
        has_assert_ast = any(isinstance(node, ast.Assert) for node in ast.walk(tree))
        has_raise_or_try = any(isinstance(node, (ast.Raise, ast.Try)) for node in ast.walk(tree))

        calls_or_assigns = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Call, ast.Assign, ast.AnnAssign))
        ]
        top_level_meaningful = [
            stmt
            for stmt in tree.body
            if not _is_docstring_expr(stmt)
            and not isinstance(stmt, (ast.Import, ast.ImportFrom, ast.Pass))
            and not (isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_stub_function(stmt))
        ]

        is_stub_only = bool(functions) and len(non_stub_functions) == 0 and len(control_flow) == 0
        has_real_impl = (len(non_stub_functions) > 0) or (
            not functions and len(top_level_meaningful) >= 2 and (len(control_flow) > 0 or len(calls_or_assigns) >= 2)
        )

        findings: list[str] = []
        if is_stub_only:
            findings.append(
                "Les fonctions Python détectées sont des squelettes vides (pass / ... / return None / NotImplementedError) sans logique réelle."
            )
        if not has_real_impl:
            findings.append(
                "Implémentation insuffisante : fournissez une logique complète (fonctions non vides, structures de contrôle ou traitements réels)."
            )
        if dangerous:
            findings.append(
                f"Primitives système potentiellement dangereuses détectées ({', '.join(dangerous)}) : aucune exécution locale autorisée."
            )

        score = 0
        if has_real_impl and not is_stub_only:
            score = 65
            if len(control_flow) >= 1:
                score += 10
            if has_edge_cases or has_raise_or_try:
                score += 12
            if has_tests or has_assert_ast:
                score += 13
            if dangerous:
                score = max(0, score - 25)
        elif not is_stub_only:
            score = 35

        return SandboxVerificationReport(
            language="python",
            syntax_valid=True,
            is_stub_only=is_stub_only,
            has_real_implementation=has_real_impl,
            has_edge_case_handling=has_edge_cases or has_raise_or_try,
            has_tests_or_assertions=has_tests or has_assert_ast,
            dangerous_constructs=dangerous,
            function_count=len(functions),
            non_stub_function_count=len(non_stub_functions),
            class_count=len(classes),
            control_flow_nodes=len(control_flow),
            quality_score=min(100, score),
            findings=findings,
        )

    # 2. Analyse statique structurée SQL / JS / TS / Web / Shell
    is_sql = any(k in lowered for k in ("select ", "create table", "insert into", "alter table", "with "))
    is_js_ts = any(k in lowered for k in ("function ", "const ", "=>", "export ", "interface ", "usestate", "useeffect"))
    is_html_css = any(k in lowered for k in ("<div", "<section", "<main", "<form", "display:", "grid-template"))

    non_empty_lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip() and not ln.strip().startswith(("//", "#", "--", "/*"))]
    stub_js = bool(re.fullmatch(r"(?:export\s+)?(?:function\s+\w+\([^)]*\)|const\s+\w+\s*=\s*\([^)]*\)\s*=>)\s*\{\s*(?:return\s*(?:null|undefined)?;?\s*|//.*)?\}", cleaned, re.DOTALL))
    has_braces_balanced = cleaned.count("{") == cleaned.count("}") and cleaned.count("(") == cleaned.count(")")

    detected_lang = "sql" if is_sql else ("js/ts" if is_js_ts else ("html/css" if is_html_css else (language_hint or "generic")))
    has_real_impl = (not stub_js) and has_braces_balanced and len(non_empty_lines) >= 3
    findings = []
    if stub_js:
        findings.append("Fonction vide/stub détectée sans implémentation réelle.")
    if not has_braces_balanced:
        findings.append("Délimiteurs () ou {} déséquilibrés : vérifiez la syntaxe du code.")
    if not has_real_impl and not findings:
        findings.append("Le bloc de code est trop minimal pour démontrer une réalisation complète.")

    score = 0
    if has_real_impl:
        score = 68
        if has_edge_cases:
            score += 15
        if has_tests:
            score += 17
        if dangerous:
            score = max(0, score - 25)

    return SandboxVerificationReport(
        language=detected_lang,
        syntax_valid=has_braces_balanced,
        is_stub_only=stub_js,
        has_real_implementation=has_real_impl,
        has_edge_case_handling=has_edge_cases,
        has_tests_or_assertions=has_tests,
        dangerous_constructs=dangerous,
        quality_score=min(100, score),
        findings=findings,
    )
