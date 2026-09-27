from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
sys.path.insert(0, str(ROOT / "tools"))

import compare_vault  # noqa: E402

# A backticked token that names something inside the vault.
VAULT_PATH = re.compile(r"`((?:[0-9]_[^`/\s]+|AGENTS\.md|CLAUDE\.md)[^`\s]*)`")
# Documents that describe the vault: the conductor, layer guides, system files.
DOCS = [ROOT / "SKILL.md", *sorted(TEMPLATES.rglob("*.md"))]
# Folders the vault creates only when needed, so the templates don't ship them.
ON_DEMAND = ("5_규범자료/_지난판/", "8_시스템/보관/", "9_형식/서식프로필/")
# Layers that hold the user's own files; paths there are examples, not system files.
USER_LAYERS = ("0_원본/", "1_파싱/", "5_규범자료/", "6_참고자료/", "7_개인정보이미지/")
# v1 folder names, mentioned only by the migration steps in SKILL.md.
LEGACY = ("1_두뇌", "2_시스템", "3_형식")


def must_exist(path: str) -> bool:
    """Decide whether a path written in the docs has to exist in templates/."""
    if any(mark in path for mark in ("<", "{", "*", "…")):
        return False  # placeholder such as `1_파싱/<파싱본 경로>`
    if path.startswith(ON_DEMAND) or path.startswith(LEGACY):
        return False
    if path.startswith(USER_LAYERS):
        # Only the fixed guide and register files of a user layer are system files.
        return path.endswith(("/_안내.md", "/자료목록.md", "/자산목록.md", "/사용기록.md"))
    return True


class PathReferenceTests(unittest.TestCase):
    def test_every_vault_path_in_the_docs_exists_in_templates(self):
        # The 2026-09-09 audit found 11 references to files that never existed and
        # 53 paths copied from another skill with the wrong base folder.
        missing = []
        for doc in DOCS:
            text = doc.read_text(encoding="utf-8")
            for match in VAULT_PATH.finditer(text):
                path = match.group(1).rstrip(".,)")
                if must_exist(path) and not (TEMPLATES / path).exists():
                    missing.append(f"{doc.relative_to(ROOT)}: `{path}`")
        self.assertEqual(missing, [], "\n" + "\n".join(missing))

    def test_example_commands_point_at_real_scripts(self):
        for doc in DOCS:
            for script in re.findall(r"py -3 (9_형식/scripts/\S+\.py)", doc.read_text(encoding="utf-8")):
                self.assertTrue((TEMPLATES / script).is_file(), f"{doc.name}: {script}")


class OwnershipTests(unittest.TestCase):
    def test_vault_owned_files_exist_in_templates(self):
        for rel in compare_vault.VAULT_OWNED_FILES:
            self.assertTrue((TEMPLATES / rel).is_file(), rel)

    def test_skill_upgrade_rules_protect_every_vault_owned_file(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        upgrade = skill.split("## 업그레이드 · 복구", 1)[1]
        for rel in compare_vault.VAULT_OWNED_FILES:
            name = rel.rsplit("/", 1)[1]
            if name in ("자료목록.md", "자산목록.md", "사용기록.md"):
                continue  # covered by "5·6·7층의 사용자 내용"과 "자산 사용 기록"
            self.assertIn(name, upgrade, f"SKILL.md 업그레이드 절이 {rel}을 보호하지 않음")

    def test_conductor_names_the_only_vault_owned_file_in_9_형식(self):
        agents = (TEMPLATES / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`9_형식/현장메모.md`만 볼트 소유", agents)


if __name__ == "__main__":
    unittest.main()
