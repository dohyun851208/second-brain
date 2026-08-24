from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ImagePolicyTests(unittest.TestCase):
    def test_system_version_is_3_7(self):
        agents = (ROOT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("시스템 버전: 3.7", agents)

    def test_required_signature_discovery_is_a_routing_trigger(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        routing = (ROOT / "templates" / "9_형식" / "라우팅.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, routing):
            self.assertIn("최초 요청", text)
            self.assertIn("서명·날인", text)
            self.assertIn("완성본으로 보고하지 않는다", text)

    def test_discovery_does_not_bypass_asset_approval(self):
        privacy = (
            ROOT / "templates" / "7_개인정보이미지" / "_안내.md"
        ).read_text(encoding="utf-8")
        self.assertIn("미승인이라면", privacy)
        self.assertIn("선택·모호한 이미지란은 자동 삽입하지 않는다", privacy)
        self.assertIn("임시 HWPX", privacy)
        self.assertIn("한 번 변환", privacy)

    def test_kordoc_exception_covers_general_raster_images(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        routing = (ROOT / "templates" / "9_형식" / "라우팅.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, routing):
            self.assertIn("place_image.py", text)
            self.assertIn("신분증", text)
            self.assertIn("통장사본", text)
            self.assertIn("일반 사진", text)
            self.assertIn("유일한 예외", text)

    def test_kordoc_generate_owns_new_document_images(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        routing = (ROOT / "templates" / "9_형식" / "라우팅.md").read_text(
            encoding="utf-8"
        )
        for text in (skill, routing):
            self.assertIn("generate --image-dir", text)
            self.assertIn("기존", text)

    def test_separate_attachment_is_not_replaced_by_embedding(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        privacy = (
            ROOT / "templates" / "7_개인정보이미지" / "_안내.md"
        ).read_text(encoding="utf-8")
        for text in (skill, privacy):
            self.assertIn("별도 파일 첨부", text)
            self.assertIn("문서 안", text)

    def test_other_private_images_have_a_safe_storage_folder(self):
        keep = (
            ROOT
            / "templates"
            / "7_개인정보이미지"
            / "기타이미지"
            / ".gitkeep"
        )
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(keep.is_file())
        self.assertIn("/templates/7_개인정보이미지/기타이미지/*", gitignore)
        self.assertIn("!/templates/7_개인정보이미지/기타이미지/.gitkeep", gitignore)


if __name__ == "__main__":
    unittest.main()
