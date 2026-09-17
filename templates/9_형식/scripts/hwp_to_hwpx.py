#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert legacy HWP to temporary HWPX for approved image placement only.

This module is internal to ``place_image.py``/``place_signature.py``. Ordinary HWP/HWPX work
must keep using Kordoc. The COM conversion sequence follows the MIT-licensed
``dohyun851208/teacher`` skill, while publishing through a private temporary
file so the source and any existing output stay untouched on failure.

Requires Windows Hancom Office and pywin32.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class HwpConversionError(RuntimeError):
    """Raised when Hancom cannot produce a verified HWPX file."""


def convert_hwp_to_hwpx(source: Path, output: Path, *, overwrite: bool = False) -> Path:
    """Convert one ``.hwp`` file to ``.hwpx`` without changing the source."""
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()

    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".hwp":
        raise ValueError(f"입력 파일 확장자는 .hwp여야 합니다: {source}")
    if output.suffix.lower() != ".hwpx":
        raise ValueError(f"변환 출력 확장자는 .hwpx여야 합니다: {output}")
    if source == output:
        raise ValueError("변환 출력 경로는 원본과 달라야 합니다.")
    if output.exists() and not overwrite:
        raise FileExistsError(f"기존 변환 출력은 덮어쓰지 않습니다: {output}")

    try:
        import win32com.client as win32
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise HwpConversionError(
            "HWP→HWPX 변환에 pywin32가 필요합니다: py -3 -m pip install pywin32"
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f".{output.stem}_",
        suffix=".hwpx",
        dir=output.parent,
    )
    os.close(temp_fd)
    temp_output = Path(temp_name)
    temp_output.unlink()

    try:
        hwp = None
        try:
            hwp = win32.Dispatch("HWPFrame.HwpObject")
            try:
                registered = hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
                if registered is False:
                    print("WARN: 한컴 파일 경로 보안 모듈이 등록되지 않았습니다.")
            except Exception:
                print("WARN: 한컴 파일 경로 보안 모듈을 등록하지 못했습니다.")

            hwp.SetMessageBoxMode(0x00020000)
            try:
                hwp.XHwpWindows.Item(0).Visible = False
            except Exception:
                pass

            opened = hwp.Open(str(source), "", "forceopen:true")
            if opened is False:
                raise HwpConversionError(f"한컴이 HWP 원본을 열지 못했습니다: {source}")
            saved = hwp.SaveAs(str(temp_output), "HWPX", "")
            if saved is False:
                raise HwpConversionError(f"한컴이 HWPX 변환본을 저장하지 못했습니다: {output}")
        except HwpConversionError:
            raise
        except Exception as exc:
            raise HwpConversionError(f"한컴 COM HWP→HWPX 변환 실패: {exc}") from exc
        finally:
            if hwp is not None:
                try:
                    hwp.Clear(1)
                    hwp.Quit()
                except Exception:
                    pass

        if not temp_output.is_file() or temp_output.stat().st_size == 0:
            raise HwpConversionError(f"한컴이 유효한 HWPX 변환본을 만들지 못했습니다: {output}")
        if output.exists() and not overwrite:
            raise FileExistsError(f"작업 중 같은 이름의 변환 출력이 생겼습니다: {output}")
        os.replace(temp_output, output)
        return output
    finally:
        if temp_output.exists():
            temp_output.unlink()
