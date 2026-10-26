"""Conservative language classification and toolchain metadata.

Classification is metadata only. It does not authorize repair generation,
dependency installation, or execution of third-party source.
"""
from __future__ import annotations

from pathlib import PurePosixPath

SUPPORTED_LANGUAGE_PROFILES = ("PYTHON", "TYPESCRIPT", "JAVASCRIPT")

_PRIMARY = {
    "python": "PYTHON",
    "typescript": "TYPESCRIPT",
    "javascript": "JAVASCRIPT",
}
_EXTENSION = {
    ".py": "PYTHON",
    ".pyi": "PYTHON",
    ".ts": "TYPESCRIPT",
    ".tsx": "TYPESCRIPT",
    ".js": "JAVASCRIPT",
    ".jsx": "JAVASCRIPT",
    ".mjs": "JAVASCRIPT",
    ".cjs": "JAVASCRIPT",
}
_SKILLS = {
    "python": "PYTHON",
    "python 3": "PYTHON",
    "typescript": "TYPESCRIPT",
    "typescript programming": "TYPESCRIPT",
    "javascript": "JAVASCRIPT",
    "javascript programming": "JAVASCRIPT",
    "node.js": "JAVASCRIPT",
    "nodejs": "JAVASCRIPT",
}


def from_repository_language(value: object) -> str:
    """Map exact GitHub repository-language metadata to a supported profile."""
    if not isinstance(value, str):
        return "UNKNOWN"
    return _PRIMARY.get(value.strip().casefold(), "OTHER")


def from_file_paths(paths: object) -> str:
    if not isinstance(paths, (list, tuple)) or not paths:
        return "UNKNOWN"
    profiles = set()
    for path in paths:
        if not isinstance(path, str) or len(path) > 512 or "\\" in path or "\x00" in path:
            return "UNKNOWN"
        pure=PurePosixPath(path)
        if pure.is_absolute() or '..' in pure.parts:
            return "UNKNOWN"
        profile = _EXTENSION.get(pure.suffix.casefold())
        if profile:
            profiles.add(profile)
    if len(profiles) == 1:
        return next(iter(profiles))
    return "MULTI_LANGUAGE" if profiles else "UNKNOWN"


def from_skills(skills: object) -> str:
    if not isinstance(skills, (list, tuple)):
        return "UNKNOWN"
    profiles = set()
    for skill in skills[:50]:
        if isinstance(skill, str):
            normalized = " ".join(skill.strip().casefold().split())
            profile = _SKILLS.get(normalized)
            if profile:
                profiles.add(profile)
    if len(profiles) == 1:
        return next(iter(profiles))
    return "MULTI_LANGUAGE" if profiles else "UNKNOWN"


def classify_task_language(*, repository_language=None, file_paths=(), skills=()) -> str:
    """Combine independent metadata conservatively; conflicting evidence is mixed."""
    evidence = set()
    primary = from_repository_language(repository_language)
    if primary in SUPPORTED_LANGUAGE_PROFILES:
        evidence.add(primary)
    files = from_file_paths(file_paths)
    if files in SUPPORTED_LANGUAGE_PROFILES:
        evidence.add(files)
    elif files == "MULTI_LANGUAGE":
        return files
    skill_profile = from_skills(skills)
    if skill_profile in SUPPORTED_LANGUAGE_PROFILES:
        evidence.add(skill_profile)
    elif skill_profile == "MULTI_LANGUAGE":
        return skill_profile
    if len(evidence) > 1:
        return "MULTI_LANGUAGE"
    if evidence:
        return next(iter(evidence))
    return primary if primary == "OTHER" else "UNKNOWN"


def toolchain_requirements(profile: str) -> dict:
    """Describe available verification levels without granting execution authority."""
    if profile == "PYTHON":
        tools = {
            "runtime": "Python 3; exact version must be pinned per task",
            "syntax_check": "python -m py_compile",
            "test_runner": "unittest or explicitly admitted pytest",
            "static_linter": "Ruff availability must be verified per runner",
            "typecheck": "mypy/pyright availability must be verified per task",
        }
    elif profile == "JAVASCRIPT":
        tools = {
            "runtime": "Node.js 24.19.0 in the current engineering workspace",
            "syntax_check": "node --check",
            "test_runner": "built-in node:test",
            "static_linter": "ESLint is not installed; no package installation admitted",
            "typecheck": "not applicable",
        }
    elif profile == "TYPESCRIPT":
        tools = {
            "runtime": "Node.js 24.19.0 built-in type stripping for erasable syntax only",
            "syntax_check": "Node.js TypeScript stripping; not a full compiler check",
            "test_runner": "built-in node:test with --experimental-strip-types",
            "static_linter": "ESLint is not installed; no package installation admitted",
            "typecheck": "tsc is not installed; full TypeScript type-checking is unavailable",
        }
    else:
        raise ValueError("SUPPORTED_LANGUAGE_PROFILE_REQUIRED")
    return {
        "profile": profile,
        "tools": tools,
        "development_fixture_execution": "OWNED_FIXTURES_ONLY",
        "third_party_execution": "NOT_ADMITTED",
        "dependency_installation": "DENIED",
        "network_access": "DENIED",
        "model_generation": "NOT_ENABLED_BY_LANGUAGE_CLASSIFICATION",
    }
