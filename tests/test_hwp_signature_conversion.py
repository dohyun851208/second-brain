from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "templates" / "9_형식" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import hwp_to_hwpx  # noqa: E402
import place_image  # noqa: E402
import place_signature  # noqa: E402


class _Window:
    Visible = True


class _Windows:
    def __init__(self) -> None:
        self.window = _Window()

    def Item(self, index: int) -> _Window:
        if index != 0:
            raise IndexError(index)
        return self.window


class _FakeHwp:
    def __init__(self, *, save_error: bool = False) -> None:
        self.XHwpWindows = _Windows()
        self.save_error = save_error
        self.calls: list[tuple] = []

    def RegisterModule(self, *args):
        self.calls.append(("RegisterModule", *args))
        return True

    def SetMessageBoxMode(self, mode):
        self.calls.append(("SetMessageBoxMode", mode))

    def Open(self, *args):
        self.calls.append(("Open", *args))
        return True

    def SaveAs(self, path, format_name, options):
        self.calls.append(("SaveAs", path, format_name, options))
        Path(path).write_bytes(b"converted-hwpx")
        if self.save_error:
            raise RuntimeError("simulated SaveAs failure")
        return True

    def Clear(self, mode):
        self.calls.append(("Clear", mode))

    def Quit(self):
        self.calls.append(("Quit",))


def _fake_win32_modules(hwp: _FakeHwp) -> dict[str, types.ModuleType]:
    package = types.ModuleType("win32com")
    client = types.ModuleType("win32com.client")
    client.Dispatch = lambda name: hwp
    package.client = client
    return {"win32com": package, "win32com.client": client}


class HwpToHwpxTests(unittest.TestCase):
    @unittest.skipUnless(
        os.name == "nt" and os.environ.get("SECOND_BRAIN_HANCOM_INTEGRATION") == "1",
        "set SECOND_BRAIN_HANCOM_INTEGRATION=1 to run the real Hancom COM test",
    )
    def test_real_hancom_hwp_to_hwpx_round_trip(self):
        import win32com.client as win32

        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "blank.hwp"
            output = folder / "blank.hwpx"

            hwp = win32.Dispatch("HWPFrame.HwpObject")
            try:
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
                hwp.SetMessageBoxMode(0x00020000)
                try:
                    hwp.XHwpWindows.Item(0).Visible = False
                except Exception:
                    pass
                hwp.HAction.Run("FileNew")
                saved = hwp.SaveAs(str(source), "HWP", "")
                self.assertIsNot(saved, False)
            finally:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass

            before = source.read_bytes()
            hwp_to_hwpx.convert_hwp_to_hwpx(source, output)

            self.assertEqual(source.read_bytes(), before)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("mimetype", archive.namelist())
                self.assertIn("Contents/section0.xml", archive.namelist())

    def test_converts_atomically_without_changing_source(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwp"
            output = folder / "form.converted.hwpx"
            source.write_bytes(b"original-hwp")
            fake_hwp = _FakeHwp()

            with patch.dict(sys.modules, _fake_win32_modules(fake_hwp)):
                result = hwp_to_hwpx.convert_hwp_to_hwpx(source, output)

            self.assertEqual(result, output.resolve())
            self.assertEqual(source.read_bytes(), b"original-hwp")
            self.assertEqual(output.read_bytes(), b"converted-hwpx")
            save_call = next(call for call in fake_hwp.calls if call[0] == "SaveAs")
            self.assertNotEqual(Path(save_call[1]), output)
            self.assertEqual(save_call[2], "HWPX")
            self.assertIn(("Clear", 1), fake_hwp.calls)
            self.assertIn(("Quit",), fake_hwp.calls)
            self.assertEqual(list(folder.glob(".form.converted_*.hwpx")), [])

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwp"
            output = folder / "form.hwpx"
            source.write_bytes(b"original-hwp")
            output.write_bytes(b"existing-output")

            with self.assertRaises(FileExistsError):
                hwp_to_hwpx.convert_hwp_to_hwpx(source, output)

            self.assertEqual(source.read_bytes(), b"original-hwp")
            self.assertEqual(output.read_bytes(), b"existing-output")

    def test_failed_conversion_removes_partial_temp_file(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source = folder / "form.hwp"
            output = folder / "form.hwpx"
            source.write_bytes(b"original-hwp")
            fake_hwp = _FakeHwp(save_error=True)

            with patch.dict(sys.modules, _fake_win32_modules(fake_hwp)):
                with self.assertRaises(hwp_to_hwpx.HwpConversionError):
                    hwp_to_hwpx.convert_hwp_to_hwpx(source, output)

            self.assertFalse(output.exists())
            self.assertEqual(list(folder.glob(".form_*.hwpx")), [])

    def test_image_router_converts_hwp_once_and_passes_hwpx_through(self):
        with tempfile.TemporaryDirectory() as raw_dir:
            folder = Path(raw_dir)
            source_hwp = folder / "form.hwp"
            source_hwpx = folder / "form.hwpx"
            source_hwp.write_bytes(b"hwp")
            source_hwpx.write_bytes(b"hwpx")

            with patch.object(
                place_signature,
                "convert_hwp_to_hwpx",
                return_value=folder / "form.converted.hwpx",
            ) as convert:
                converted = place_signature._prepare_hwpx_source(source_hwp, folder)
                direct = place_signature._prepare_hwpx_source(source_hwpx, folder)

            self.assertEqual(convert.call_count, 1)
            self.assertEqual(converted.suffix, ".hwpx")
            self.assertEqual(direct, source_hwpx)

    def test_generic_entrypoint_keeps_legacy_command_compatible(self):
        self.assertIs(place_image.main, place_signature.main)


if __name__ == "__main__":
    unittest.main()
