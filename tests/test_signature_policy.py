from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def read(*parts: str) -> str:
    return TEMPLATES.joinpath(*parts).read_text(encoding="utf-8")


# Each rule is checked in the one file that owns it. Other files point there
# instead of repeating it: three copies of the ".hwp에 fill 금지" rule did not
# stop it from being broken on 2026-09-20, and every copy had to be edited
# whenever the rule changed.
class ImagePolicyTests(unittest.TestCase):
    def test_system_version_is_3_10(self):
        self.assertIn("시스템 버전: 3.10", read("AGENTS.md"))

    def test_conductor_keeps_the_rules_that_fail_silently(self):
        agents = read("AGENTS.md")
        self.assertIn("`.hwp`에 `fill`을 쓰지 않는다", agents)
        self.assertIn("exit 2", agents)
        self.assertIn("완성본이라 하지 않는다", agents)
        self.assertIn("최초 요청에 없었어도", agents)
        self.assertIn("`9_형식/scripts/place_image.py` 하나뿐", agents)

    def test_vault_routing_wins_over_other_skills(self):
        agents = read("AGENTS.md")
        routing = read("9_형식", "라우팅.md")
        for text in (agents, routing):
            self.assertIn("teacher", text)
        self.assertIn("이 볼트의 한글·서명 작업은 `9_형식/라우팅.md`를 따른다", agents)

    def test_required_signature_discovery_is_a_routing_trigger(self):
        routing = read("9_형식", "라우팅.md")
        self.assertIn("최초 요청", routing)
        self.assertIn("서명·날인", routing)
        self.assertIn("완성본으로 보고하지 않는다", routing)

    def test_discovery_does_not_bypass_asset_approval(self):
        privacy = read("7_개인정보이미지", "_안내.md")
        self.assertIn("미승인이라면", privacy)
        self.assertIn("선택·모호한 이미지란은 자동 삽입하지 않는다", privacy)

    def test_kordoc_exception_covers_general_raster_images(self):
        routing = read("9_형식", "라우팅.md")
        for term in ("place_image.py", "신분증", "통장사본", "일반 사진", "유일한 예외"):
            self.assertIn(term, routing)

    def test_kordoc_generate_owns_new_document_images(self):
        routing = read("9_형식", "라우팅.md")
        self.assertIn("generate --image-dir", routing)
        self.assertIn("기존", routing)

    def test_hwp_conversion_stays_inside_the_image_exception(self):
        routing = read("9_형식", "라우팅.md")
        self.assertIn("승인된 이미지 배치 작업 안에서만", routing)
        self.assertIn("*_완성본.hwpx", routing)

    def test_image_commands_live_in_one_workflow(self):
        workflow = read("9_형식", "references", "workflows", "hwpx-forms.md")
        routing = read("9_형식", "라우팅.md")
        self.assertIn("py -3 9_형식/scripts/place_image.py", workflow)
        self.assertNotIn("py -3 9_형식/scripts/place_image.py", routing)
        self.assertIn("hwpx-forms.md` 3절", routing)

    def test_seal_is_not_a_fallback(self):
        # Kordoc 4.15.6 seal was measured on 2026-09-28: invisible by default,
        # misplaced and squashed with explicit sizes, and no .hwp input.
        kordoc = read("9_형식", "references", "kordoc.md")
        self.assertIn("4.15.6 실측", kordoc)
        for text in (
            read("9_형식", "라우팅.md"),
            read("9_형식", "references", "workflows", "hwpx-forms.md"),
            kordoc,
        ):
            self.assertNotIn("서명은 Kordoc `seal`로", text)
            self.assertNotIn("서명은 `seal`로", text)

    def test_pdf_attachments_are_cropped_before_placement(self):
        workflow = read("9_형식", "references", "workflows", "hwpx-forms.md")
        self.assertIn("PDF면 먼저 PNG로", workflow)
        self.assertIn("300dpi", workflow)

    def test_separate_attachment_is_not_replaced_by_embedding(self):
        privacy = read("7_개인정보이미지", "_안내.md")
        self.assertIn("별도 파일 첨부", privacy)
        self.assertIn("문서 안", privacy)

    def test_other_private_images_have_a_safe_storage_folder(self):
        keep = TEMPLATES / "7_개인정보이미지" / "기타이미지" / ".gitkeep"
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertTrue(keep.is_file())
        self.assertIn("/templates/7_개인정보이미지/기타이미지/*", gitignore)
        self.assertIn("!/templates/7_개인정보이미지/기타이미지/.gitkeep", gitignore)


if __name__ == "__main__":
    unittest.main()
