from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class KordocPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = (
            ROOT / "templates" / "9_형식" / "references" / "kordoc.md"
        ).read_text(encoding="utf-8")

    def test_reviewed_version_and_range_are_explicit(self):
        self.assertIn("@^4", self.reference)
        self.assertIn("4.9.2", self.reference)
        self.assertIn("엔진 소스", self.reference)

    def test_v4_parse_contract_is_documented(self):
        for term in (
            "metadata.pageMode",
            "pages[]",
            "--no-tables",
            "--image-refs",
            "--password",
        ):
            self.assertIn(term, self.reference)

    def test_lint_contract_uses_text_and_munche(self):
        self.assertIn("--munche", self.reference)
        self.assertIn("`md`/`txt`", self.reference)
        self.assertIn("HWP/HWPX/PDF를 직접 넘기지", self.reference)

    def test_new_and_existing_document_image_routes_are_distinct(self):
        self.assertIn("generate --image-dir", self.reference)
        self.assertIn("기존 문서의 지정 위치", self.reference)
        self.assertIn("place_image.py", self.reference)


if __name__ == "__main__":
    unittest.main()
