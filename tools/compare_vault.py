#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare a Second Brain vault's system files with this skill's templates/.

Read-only. Run it before an upgrade: the system version number cannot tell that
someone edited a system file inside the vault, so this compares file contents.
CRLF/LF differences and the ``{{이름}}`` substitution in AGENTS.md count as equal.

When the skill folder is a git checkout, a differing file is also checked against
every past version of its template. A match means the vault is simply behind and
is safe to update; no match means the vault holds its own edits, which must be
moved to 9_형식/현장메모.md or promoted to the skill before anything is replaced.

    py -3 tools/compare_vault.py <vault path>
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL / "templates"
NAME_TOKEN = "{{이름}}"

# Files the vault fills in. Their contents are expected to differ from the
# templates; only a missing file is reported. Keep in sync with the protected
# list in SKILL.md "업그레이드 · 복구" (tests/test_structure.py checks this).
VAULT_OWNED_DIRS = ("2_두뇌/",)
VAULT_OWNED_FILES = {
    "5_규범자료/자료목록.md",
    "6_참고자료/자료목록.md",
    "7_개인정보이미지/자산목록.md",
    "7_개인정보이미지/사용기록.md",
    "8_시스템/log.md",
    "8_시스템/가설-기록.md",
    "9_형식/현장메모.md",
}
SYSTEM_DIRS = ("8_시스템", "9_형식")
IGNORED_PARTS = {"__pycache__", "보관"}


def is_vault_owned(rel: str) -> bool:
    return rel in VAULT_OWNED_FILES or rel.startswith(VAULT_OWNED_DIRS)


def normalise(data: bytes, name: str | None) -> bytes:
    data = data.replace(b"\r\n", b"\n")
    if name:
        data = data.replace(name.encode("utf-8"), NAME_TOKEN.encode("utf-8"))
    return data


def vault_name(vault: Path) -> str | None:
    try:
        text = (vault / "AGENTS.md").read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"이 볼트는 (.+?)의 Second Brain이다", text)
    return match.group(1) if match else None


def system_version(path: Path) -> str:
    try:
        match = re.search(r"시스템 버전: ([\d.]+)", path.read_text(encoding="utf-8"))
    except OSError:
        return "?"
    return match.group(1) if match else "?"


def template_files() -> list[str]:
    return sorted(
        p.relative_to(TEMPLATES).as_posix()
        for p in TEMPLATES.rglob("*")
        if p.is_file() and p.name != ".gitkeep" and "__pycache__" not in p.parts
    )


def matches_past_template(rel: str, content: bytes, name: str | None) -> bool | None:
    """True if the vault copy equals some committed version of the template."""
    git_path = f"templates/{rel}"
    try:
        shas = subprocess.run(
            ["git", "-C", str(SKILL), "log", "--format=%H", "--", git_path],
            capture_output=True, check=True,
        ).stdout.decode().split()
    except (OSError, subprocess.CalledProcessError):
        return None
    for sha in shas:
        old = subprocess.run(
            ["git", "-C", str(SKILL), "show", f"{sha}:{git_path}"], capture_output=True
        )
        if old.returncode == 0 and normalise(old.stdout, None) == content:
            return True
    return False if shas else None


def compare(vault: Path) -> dict[str, list[str]]:
    name = vault_name(vault)
    result: dict[str, list[str]] = {
        "same": [], "behind": [], "edited": [], "differs": [], "new": [],
        "owned_missing": [], "stale": [], "work": [],
    }
    known = set(template_files())
    for rel in sorted(known):
        target = vault / rel
        if is_vault_owned(rel):
            if not target.is_file():
                result["owned_missing"].append(rel)
            continue
        if not target.is_file():
            result["new"].append(rel)
            continue
        ours = normalise((TEMPLATES / rel).read_bytes(), None)
        theirs = normalise(target.read_bytes(), name)
        if ours == theirs:
            result["same"].append(rel)
            continue
        past = matches_past_template(rel, theirs, name)
        key = {True: "behind", False: "edited", None: "differs"}[past]
        result[key].append(rel)
    for folder in SYSTEM_DIRS:
        root = vault / folder
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            rel = path.relative_to(vault).as_posix()
            parts = path.relative_to(root).parts
            if not path.is_file() or rel in known or set(parts) & IGNORED_PARTS:
                continue
            # "_" folders such as 9_형식/_작업/ hold the user's work, not old system files.
            is_work = any(part.startswith("_") for part in parts[:-1])
            result["work" if is_work else "stale"].append(rel)
    return result


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("사용법: py -3 tools/compare_vault.py <볼트 경로>")
        return 2
    vault = Path(args[0]).expanduser().resolve()
    if not (vault / "AGENTS.md").is_file():
        print(f"볼트가 아닙니다(AGENTS.md 없음): {vault}")
        return 2

    r = compare(vault)
    print(f"스킬 시스템 버전 {system_version(TEMPLATES / 'AGENTS.md')} / "
          f"볼트 시스템 버전 {system_version(vault / 'AGENTS.md')}\n")
    total = sum(len(r[k]) for k in ("same", "behind", "edited", "differs", "new"))
    print(f"시스템 파일 {total}개 — 같음 {len(r['same'])}")
    sections = [
        ("behind", "볼트가 옛 판 (교체해도 잃는 것 없음)"),
        ("edited", "볼트에서 직접 고친 내용 있음 — 교체 전에 현장메모로 옮기거나 스킬로 승격"),
        ("differs", "다름 (이력이 없어 옛 판인지 직접 고친 것인지 판단 불가 — 내용을 보고 결정)"),
        ("new", "볼트에 없음 (새로 생긴 시스템 파일)"),
        ("owned_missing", "볼트 소유 파일이 없음 (빈 템플릿으로 만들 대상)"),
        ("stale", "스킬에 없는 옛 시스템 파일 (8_시스템/보관/ 이동 후보)"),
        ("work", "시스템 폴더 안의 작업물 (시스템 파일 아님 — 둘지 옮길지는 사용자가 정함)"),
    ]
    for key, label in sections:
        if r[key]:
            print(f"\n{label}: {len(r[key])}개")
            for rel in r[key]:
                print(f"   {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
