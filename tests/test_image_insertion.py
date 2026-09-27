from __future__ import annotations

import base64
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "templates" / "9_형식" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import insert_signature_hwpx  # noqa: E402
import place_signature  # noqa: E402


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


STILL_LAYOUT = [[("사진", 10.0, 10.0)]]


def _write_minimal_hwpx(
    path: Path, paragraphs: str | None = None, declare_core: bool = True
) -> None:
    body = paragraphs or '<hp:p><hp:run charPrIDRef="1"><hp:t>사진</hp:t></hp:run></hp:p>'
    core = ' xmlns:hc="urn:hc"' if declare_core else ""
    section = f"""<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hs="urn:hs" xmlns:hp="urn:hp"{core}>
  {body}
</hs:sec>
"""
    header = """<?xml version="1.0" encoding="UTF-8"?>
<hh:head xmlns:hh="urn:hh"><hh:charPr id="1" height="1000"/></hh:head>
"""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<opf:package xmlns:opf="urn:opf"><opf:manifest></opf:manifest></opf:package>
"""
    with zipfile.ZipFile(path, "w") as archive:
        mimetype = zipfile.ZipInfo("mimetype")
        mimetype.compress_type = zipfile.ZIP_STORED
        archive.writestr(mimetype, b"application/hwp+zip")
        archive.writestr("Contents/section0.xml", section)
        archive.writestr("Contents/header.xml", header)
        archive.writestr("Contents/content.hpf", content)


class GenericImageInsertionTests(unittest.TestCase):
    def test_generic_cli_accepts_top_left_coordinates(self):
        args = place_signature.parse_args(
            [
                "form.hwpx",
                "bank-copy.jpg",
                "--anchor-para",
                "첨부 이미지",
                "--target-left-mm",
                "25",
                "--target-top-mm",
                "120",
            ]
        )
        self.assertEqual(args.image, "bank-copy.jpg")
        self.assertEqual(args.target_left_mm, 25)
        self.assertEqual(args.target_top_mm, 120)
        self.assertIsNone(args.target_bottom_mm)

    def test_non_finite_coordinates_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwpx"
            image = folder / "photo.png"
            source.write_bytes(b"source")
            image.write_bytes(b"image")
            with self.assertRaisesRegex(SystemExit, "유한한 숫자"):
                place_signature.main(
                    [str(source), str(image), "--width-mm", "nan", "--report"]
                )

    def test_internal_writer_embeds_a_non_signature_image(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwpx"
            image = folder / "bank-copy.png"
            output = folder / "form-with-image.hwpx"
            second_image = folder / "id-card.png"
            second_output = folder / "form-with-two-images.hwpx"
            _write_minimal_hwpx(source)
            image.write_bytes(PNG_1X1)
            second_image.write_bytes(PNG_1X1)

            result = insert_signature_hwpx.insert_image(
                source=source,
                image=image,
                output=output,
                anchor="사진",
                occurrence="last",
                width_hwpunit=7200,
                overwrite=False,
            )

            self.assertEqual(result[0], output.resolve())
            self.assertEqual(result[3:], (7200, 7200))
            with zipfile.ZipFile(output) as archive:
                self.assertIn("BinData/image.png", archive.namelist())
                self.assertEqual(archive.read("BinData/image.png"), PNG_1X1)
                section = archive.read("Contents/section0.xml").decode("utf-8")
                manifest = archive.read("Contents/content.hpf").decode("utf-8")
            self.assertIn('binaryItemIDRef="image"', section)
            self.assertIn('media-type="image/png"', manifest)

            insert_signature_hwpx.insert_image(
                source=output,
                image=second_image,
                output=second_output,
                anchor="사진",
                occurrence="last",
                width_hwpunit=3600,
                overwrite=False,
            )
            with zipfile.ZipFile(second_output) as archive:
                self.assertIn("BinData/image.png", archive.namelist())
                self.assertIn("BinData/image2.png", archive.namelist())
                manifest = archive.read("Contents/content.hpf").decode("utf-8")
            self.assertIn('id="image"', manifest)
            self.assertIn('id="image2"', manifest)

    def test_first_paragraph_anchor_keeps_section_definition_first(self):
        # A title is the usual "unique paragraph above the target", but the first
        # paragraph's leading run carries the page margins. Hancom ignores them when
        # a picture run comes first, and the whole form silently shifts.
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwpx"
            image = folder / "seal.png"
            output = folder / "form-sealed.hwpx"
            _write_minimal_hwpx(
                source,
                '<hp:p><hp:run charPrIDRef="1"><hp:secPr id=""/>'
                '<hp:ctrl><hp:colPr id=""/></hp:ctrl></hp:run>'
                '<hp:run charPrIDRef="1"><hp:t>신청서</hp:t></hp:run></hp:p>'
                '<hp:p><hp:run charPrIDRef="1"><hp:t>담임 확인 (인)</hp:t></hp:run></hp:p>',
            )
            image.write_bytes(PNG_1X1)

            insert_signature_hwpx.insert_image(
                source=source,
                image=image,
                output=output,
                anchor="",
                occurrence="first",
                width_hwpunit=3600,
                overwrite=False,
                placement="overlay",
                vert_offset_hwpunit=7200,
                horz_offset_hwpunit=7200,
                anchor_para="신청서",
            )
            with zipfile.ZipFile(output) as archive:
                section = archive.read("Contents/section0.xml").decode("utf-8")
            first_run = insert_signature_hwpx.RUN_RE.search(section).group(0)
            self.assertIn("<hp:secPr", first_run)
            self.assertLess(section.index("<hp:secPr"), section.index("<hp:pic"))

    def test_section_without_core_namespace_gets_it_declared(self):
        # Kordoc-generated HWPX declares only hs: and hp: on the section root, but
        # the picture XML needs hc:. The writer must add it instead of crashing.
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "generated.hwpx"
            image = folder / "sign.png"
            output = folder / "generated-signed.hwpx"
            _write_minimal_hwpx(source, declare_core=False)
            image.write_bytes(PNG_1X1)

            insert_signature_hwpx.insert_image(
                source=source,
                image=image,
                output=output,
                anchor="",
                occurrence="first",
                width_hwpunit=3600,
                overwrite=False,
                placement="overlay",
                vert_offset_hwpunit=0,
                horz_offset_hwpunit=0,
                anchor_para="사진",
            )
            with zipfile.ZipFile(output) as archive:
                section = archive.read("Contents/section0.xml").decode("utf-8")
            self.assertIn("xmlns:hc=", section.split(">", 2)[1])
            self.assertIn("<hc:img", section)

    def test_repeated_text_is_ordered_top_to_bottom(self):
        # PyMuPDF returns matches in drawing order. Hancom drew the table after the
        # signature line, so "last" (the default) picked the name in the table.
        signature_line = SimpleNamespace(x0=100.0, y0=290.0)
        table_cell = SimpleNamespace(x0=200.0, y0=120.0)
        same_line_right = SimpleNamespace(x0=300.0, y0=290.3)
        ordered = place_signature.reading_order([signature_line, same_line_right, table_cell])
        self.assertEqual(ordered, [table_cell, signature_line, same_line_right])

    def test_downscaled_render_of_a_high_resolution_image_is_recognised(self):
        # Hancom's PDF export caps pictures at about 500 dpi, so a 600px-wide
        # signature shown 24mm wide comes back as 472px. Same shape, fewer pixels.
        rendered = [{"px": (472, 173), "bbox": (47.5, 97.0, 71.5, 105.8)}]
        bbox = place_signature.pick_inserted_image(rendered, [], 24.0, 600 / 220, (600, 220))
        self.assertEqual(bbox, (47.5, 97.0, 71.5, 105.8))

    def test_image_with_a_different_pixel_shape_is_not_mistaken_for_the_insert(self):
        rendered = [{"px": (472, 300), "bbox": (47.5, 97.0, 71.5, 105.8)}]
        with self.assertRaisesRegex(SystemExit, "식별하지 못했습니다"):
            place_signature.pick_inserted_image(rendered, [], 24.0, 600 / 220, (600, 220))

    def test_top_left_target_is_measured_and_published(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwpx"
            image = folder / "photo.png"
            output = folder / "result.hwpx"
            source.write_bytes(b"source")
            image.write_bytes(b"image")

            def fake_export(_source: Path, pdf: Path) -> None:
                pdf.write_bytes(b"pdf")

            def fake_read(pdf: Path, _page: int):
                if pdf.name == "source.pdf":
                    return [], [], (210.0, 297.0)
                if pdf.name == "probe.pdf":
                    return [{"px": (100, 50), "bbox": (100.0, 5.0, 124.0, 17.0)}], [], (210.0, 297.0)
                return [{"px": (100, 50), "bbox": (30.0, 40.0, 110.0, 80.0)}], [], (210.0, 297.0)

            inserted_widths: list[int] = []

            def fake_insert(**kwargs):
                inserted_widths.append(kwargs["width_hwpunit"])
                Path(kwargs["output"]).write_bytes(b"candidate")
                return kwargs["output"], "image", "BinData/image.png", 1, 1

            with (
                patch.object(place_signature, "image_size", return_value=(100, 50)),
                patch.object(place_signature, "_prepare_hwpx_source", side_effect=lambda path, _temp: path),
                patch.object(place_signature, "export_pdf", side_effect=fake_export),
                patch.object(place_signature, "read_page", side_effect=fake_read),
                patch.object(place_signature, "insert_image", side_effect=fake_insert),
                patch.object(place_signature, "read_text_layout", return_value=STILL_LAYOUT),
            ):
                result = place_signature.main(
                    [
                        str(source),
                        str(image),
                        "--output",
                        str(output),
                        "--anchor-para",
                        "사진",
                        "--target-left-mm",
                        "30",
                        "--target-top-mm",
                        "40",
                        "--width-mm",
                        "80",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(output.read_bytes(), b"candidate")
            self.assertEqual(
                inserted_widths,
                [round(24 * 7200 / 25.4), round(80 * 7200 / 25.4)],
            )

    def test_target_outside_page_is_rejected_before_publish(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwpx"
            image = folder / "photo.png"
            output = folder / "result.hwpx"
            source.write_bytes(b"source")
            image.write_bytes(b"image")

            def fake_export(_source: Path, pdf: Path) -> None:
                pdf.write_bytes(b"pdf")

            def fake_read(pdf: Path, _page: int):
                if pdf.name == "source.pdf":
                    return [], [], (210.0, 297.0)
                return [{"px": (100, 50), "bbox": (100.0, 5.0, 124.0, 17.0)}], [], (210.0, 297.0)

            def fake_insert(**kwargs):
                Path(kwargs["output"]).write_bytes(b"candidate")
                return kwargs["output"], "image", "BinData/image.png", 1, 1

            with (
                patch.object(place_signature, "image_size", return_value=(100, 50)),
                patch.object(place_signature, "_prepare_hwpx_source", side_effect=lambda path, _temp: path),
                patch.object(place_signature, "export_pdf", side_effect=fake_export),
                patch.object(place_signature, "read_page", side_effect=fake_read),
                patch.object(place_signature, "insert_image", side_effect=fake_insert),
                patch.object(place_signature, "read_text_layout", return_value=STILL_LAYOUT),
            ):
                with self.assertRaisesRegex(SystemExit, "쪽 경계를 벗어납니다"):
                    place_signature.main(
                        [
                            str(source),
                            str(image),
                            "--output",
                            str(output),
                            "--anchor-para",
                            "사진",
                            "--target-left-mm",
                            "200",
                            "--target-top-mm",
                            "40",
                        ]
                    )

            self.assertFalse(output.exists())

    def test_layout_change_names_the_first_word_that_moved(self):
        before = [[("신청인", 20.0, 99.0), ("홍길동", 34.8, 99.0)]]
        self.assertIsNone(place_signature.layout_change(before, [[("신청인", 20.2, 99.1), ("홍길동", 34.8, 99.0)]]))
        moved = place_signature.layout_change(before, [[("신청인", 30.0, 99.0), ("홍길동", 44.8, 99.0)]])
        self.assertIn("신청인", moved)
        self.assertIn("+10.0mm", moved)
        self.assertIn("쪽 수", place_signature.layout_change(before, before + [[]]))

    def _run_main_with_layouts(self, layouts_by_pdf, inserted_offsets):
        """Drive main() with fake renders; layouts_by_pdf maps a PDF name to layouts in call order."""
        folder = Path(self._tmp.name)
        source = folder / "form.hwpx"
        image = folder / "photo.png"
        output = folder / "result.hwpx"
        source.write_bytes(b"source")
        image.write_bytes(b"image")

        def fake_export(_source: Path, pdf: Path) -> None:
            pdf.write_bytes(b"pdf")

        def fake_read(pdf: Path, _page: int):
            if pdf.name == "source.pdf":
                return [], [], (210.0, 297.0)
            if pdf.name == "probe.pdf":
                # A page whose column and paragraph origin is (0, 0): the probe
                # lands exactly at the offsets it was given.
                horz, vert = (value * 25.4 / 7200 for value in inserted_offsets[-1])
                return [{"px": (100, 50), "bbox": (horz, vert, horz + 24.0, vert + 12.0)}], [], (210.0, 297.0)
            return [{"px": (100, 50), "bbox": (30.0, 40.0, 110.0, 80.0)}], [], (210.0, 297.0)

        def fake_layout(pdf: Path):
            queue = layouts_by_pdf.get(pdf.name, [STILL_LAYOUT])
            return queue.pop(0) if len(queue) > 1 else queue[0]

        def fake_insert(**kwargs):
            inserted_offsets.append((kwargs["horz_offset_hwpunit"], kwargs["vert_offset_hwpunit"]))
            Path(kwargs["output"]).write_bytes(b"candidate")
            return kwargs["output"], "image", "BinData/image.png", 1, 1

        with (
            patch.object(place_signature, "image_size", return_value=(100, 50)),
            patch.object(place_signature, "_prepare_hwpx_source", side_effect=lambda path, _temp: path),
            patch.object(place_signature, "export_pdf", side_effect=fake_export),
            patch.object(place_signature, "read_page", side_effect=fake_read),
            patch.object(place_signature, "insert_image", side_effect=fake_insert),
            patch.object(place_signature, "read_text_layout", side_effect=fake_layout),
        ):
            place_signature.main(
                [str(source), str(image), "--output", str(output), "--anchor-para", "사진",
                 "--target-left-mm", "30", "--target-top-mm", "40", "--width-mm", "80"]
            )
        return output

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_result_that_moves_text_is_not_published(self):
        shifted = [[("사진", 10.0, 54.0)]]
        with self.assertRaisesRegex(SystemExit, "원본 배치가 바뀌었습니다"):
            self._run_main_with_layouts({"candidate1.pdf": [shifted]}, [])
        self.assertFalse((Path(self._tmp.name) / "result.hwpx").exists())

    def test_probe_that_moves_text_is_retried_at_the_anchor_corner(self):
        # On a two-page form the default probe spot pushed table rows to page 2.
        shifted = [[("사진", 10.0, 54.0)]]
        offsets: list[tuple[int, int]] = []
        output = self._run_main_with_layouts({"probe.pdf": [shifted, STILL_LAYOUT]}, offsets)
        self.assertTrue(output.exists())
        self.assertEqual(offsets[1], (0, 0))

    def test_export_is_tried_again_when_hancom_writes_nothing(self):
        calls = []

        def flaky(_hwpx: Path, pdf: Path) -> None:
            calls.append(pdf)
            if len(calls) == 2:
                pdf.write_bytes(b"%PDF")

        pdf = Path(self._tmp.name) / "out.pdf"
        with patch.object(place_signature, "_export_once", side_effect=flaky):
            place_signature.export_pdf(Path("form.hwpx"), pdf)
        self.assertEqual(len(calls), 2)

        pdf.unlink()
        with patch.object(place_signature, "_export_once", return_value=None):
            with self.assertRaisesRegex(SystemExit, "렌더링 실패"):
                place_signature.export_pdf(Path("form.hwpx"), pdf)

    def test_legacy_internal_name_remains_available(self):
        self.assertTrue(callable(insert_signature_hwpx.insert_signature))


if __name__ == "__main__":
    unittest.main()
