"""Check local prerequisites without printing secret values."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend"
VOICE_SECURITY_ROOT = REPO_ROOT.parent / "VoiceSecurity"

REQUIRED_IMPORTS = ("fastapi", "uvicorn", "sqlalchemy", "aiosqlite", "numpy", "av")
REQUIRED_MODELS = (
    VOICE_SECURITY_ROOT / "models" / "aasist" / "aasist.onnx",
    VOICE_SECURITY_ROOT / "models" / "ecapa" / "embedding_model.ckpt",
)


def check(label: str, condition: bool, detail: str) -> bool:
    state = "OK" if condition else "MISSING"
    print(f"[{state}] {label}: {detail}")
    return condition


def main() -> int:
    results: list[bool] = [
        check("Python", sys.version_info >= (3, 10), sys.version.split()[0]),
        check("Backend directory", BACKEND_ROOT.is_dir(), str(BACKEND_ROOT)),
        check("Frontend directory", FRONTEND_ROOT.is_dir(), str(FRONTEND_ROOT)),
        check("Frontend lockfile", (FRONTEND_ROOT / "package-lock.json").is_file(), "package-lock.json"),
        check("Backend environment file", (BACKEND_ROOT / ".env").is_file(), "create it from .env.example"),
        check("VoiceSecurity project", VOICE_SECURITY_ROOT.is_dir(), "expected beside echogaurd"),
        check(
            "Database configuration",
            bool(os.getenv("DATABASE_URL")) or (BACKEND_ROOT / ".env.example").is_file(),
            "DATABASE_URL is configured or the example is available",
        ),
    ]

    for module_name in REQUIRED_IMPORTS:
        results.append(
            check(
                f"Python import {module_name}",
                importlib.util.find_spec(module_name) is not None,
                "installed",
            )
        )

    for model_path in REQUIRED_MODELS:
        results.append(check(f"Model {model_path.name}", model_path.is_file(), str(model_path)))

    passed = sum(results)
    print(f"\nSetup checks: {passed}/{len(results)} passed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
