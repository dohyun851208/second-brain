from __future__ import annotations

import base64
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "templates" / "9_형식" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import insert_signature_hwpx  # noqa: E402
import place_signature  # noqa: E402


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _write_minimal_hwpx(path: Path) -> None:
    section = """<?xml version="1.0" encoding="UTF-8"?>
<hs:sec xmlns:hs="urn:hs" xmlns:hp="urn:hp" xmlns:hc="urn:hc">
  <hp:p><hp:run charPrIDRef="1"><hp:t>사진</hp:t></hp:run></hp:p>
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

    def test_legacy_internal_name_remains_available(self):
        self.assertTrue(callable(insert_signature_hwpx.insert_signature))


if __name__ == "__main__":
    unittest.main()
