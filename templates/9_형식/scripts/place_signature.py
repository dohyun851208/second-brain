#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Place an approved signature or stamp image precisely on an HWPX form.

The HWPX picture offsets used by Hancom depend on layout origins that cannot be
reliably inferred from XML alone. This script measures the actual render:

1. render the untouched source as a baseline,
2. insert a probe image at a known offset and render it,
3. solve the real layout origin,
4. build and render a candidate,
5. publish the candidate only when the measured error is within tolerance.

The source and any existing output remain untouched on failure. Temporary HWPX
and PDF files are removed. The internal XML writer is
insert_signature_hwpx.py; do not call it directly in the normal workflow.

Requires Windows Hancom Office, pywin32, and PyMuPDF.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from insert_signature_hwpx import image_size, insert_signature, unique_output_path  # noqa: E402

MM_PER_PT = 25.4 / 72
PROBE_HORZ_MM = 100.0
PROBE_VERT_MM = 5.0


def export_pdf(hwpx: Path, pdf: Path) -> None:
    """Export through Hancom COM without saving the source HWPX."""
    try:
        import win32com.client as win32
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit("pywin32가 필요합니다: py -3 -m pip install pywin32") from exc

    hwp = win32.Dispatch("HWPFrame.HwpObject")
    try:
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            print("WARN: 한컴 파일 경로 보안 모듈을 등록하지 못했습니다.")
        hwp.SetMessageBoxMode(0x00020000)
        try:
            hwp.XHwpWindows.Item(0).Visible = False
        except Exception:
            pass
        hwp.Open(str(hwpx), "", "forceopen:true")
        if pdf.exists():
            pdf.unlink()
        hwp.SaveAs(str(pdf), "PDF", "")
    finally:
        try:
            hwp.Clear(1)
            hwp.Quit()
        except Exception:
            pass

    if not pdf.exists() or pdf.stat().st_size == 0:
        raise SystemExit(f"한컴 PDF 렌더링 실패: {pdf}")


def read_page(pdf: Path, page_no: int = 0):
    """Return images, words, and page size with coordinates in millimetres."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit("PyMuPDF가 필요합니다: py -3 -m pip install pymupdf") from exc

    doc = fitz.open(pdf)
    try:
        if page_no < 0 or page_no >= len(doc):
            raise SystemExit(f"쪽 번호 범위 오류: {page_no} (전체 {len(doc)}쪽)")
        page = doc[page_no]
        images = [
            {
                "px": (info["width"], info["height"]),
                "bbox": tuple(v * MM_PER_PT for v in info["bbox"]),
            }
            for info in page.get_image_info(xrefs=True)
        ]
        words = [
            {"text": w[4], "bbox": tuple(v * MM_PER_PT for v in w[:4])}
            for w in page.get_text("words")
        ]
        rect = (page.rect.width * MM_PER_PT, page.rect.height * MM_PER_PT)
        return images, words, rect
    finally:
        doc.close()


def find_phrase(pdf: Path, needle: str, occurrence: str, page_no: int = 0):
    """Locate text on a rendered page and return its bbox in millimetres."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("PyMuPDF가 필요합니다: py -3 -m pip install pymupdf") from exc

    doc = fitz.open(pdf)
    try:
        if page_no < 0 or page_no >= len(doc):
            raise SystemExit(f"쪽 번호 범위 오류: {page_no} (전체 {len(doc)}쪽)")
        hits = doc[page_no].search_for(needle)
    finally:
        doc.close()
    if not hits:
        raise SystemExit(f"본문에서 찾지 못했습니다: {needle!r}")
    hit = hits[0] if occurrence == "first" else hits[-1]
    return tuple(v * MM_PER_PT for v in hit)


def _same_rendered_image(left: dict, right: dict, tolerance_mm: float = 0.15) -> bool:
    if left["px"] != right["px"]:
        return False
    return max(abs(a - b) for a, b in zip(left["bbox"], right["bbox"])) <= tolerance_mm


def pick_inserted_image(
    images: list[dict],
    baseline_images: list[dict],
    want_width_mm: float,
    aspect: float,
    source_px: tuple[int, int],
):
    """Identify the newly inserted image without confusing it with form images."""
    candidates = []
    for image in images:
        x0, y0, x1, y1 = image["bbox"]
        width, height = x1 - x0, y1 - y0
        if height <= 0:
            continue
        width_error = abs(width - want_width_mm)
        aspect_error = abs((width / height) - aspect)
        pixel_error = abs(image["px"][0] - source_px[0]) + abs(image["px"][1] - source_px[1])
        if width_error > 0.6 or aspect_error > 0.03 * aspect or pixel_error > 4:
            continue
        is_baseline = any(_same_rendered_image(image, old) for old in baseline_images)
        score = width_error + aspect_error + pixel_error / 1000
        candidates.append((is_baseline, score, image))

    added = [item for item in candidates if not item[0]]
    pool = added or candidates
    if not pool:
        raise SystemExit(
            f"렌더링된 쪽에서 삽입 이미지를 식별하지 못했습니다 "
            f"(폭 {want_width_mm}mm, 비율 {aspect:.2f}, 원본 {source_px[0]}x{source_px[1]}px)."
        )
    pool.sort(key=lambda item: item[1])
    if len(pool) > 1 and abs(pool[0][1] - pool[1][1]) < 1e-6:
        raise SystemExit("같은 크기와 비율의 삽입 이미지가 여러 개라 대상을 안전하게 구분하지 못했습니다.")
    return pool[0][2]["bbox"]


def derive_target(line_bbox, images, words, signature_bbox, width_mm, height_mm, gap_mm):
    """Start at the typed text end, centre on its line, and avoid marks below."""
    _, line_top, line_right, line_bottom = line_bbox
    left = line_right
    right = left + width_mm
    centred_bottom = (line_top + line_bottom) / 2 + height_mm / 2

    def overlaps(bbox):
        return not (bbox[2] <= left + 0.2 or bbox[0] >= right - 0.2)

    obstacles = []
    for image in images:
        if image["bbox"] == signature_bbox:
            continue
        if image["bbox"][1] >= line_bottom - 0.2 and overlaps(image["bbox"]):
            obstacles.append((image["bbox"][1], f"그림 {image['px'][0]}x{image['px'][1]}px"))
    for word in words:
        if word["bbox"][1] >= line_bottom - 0.2 and overlaps(word["bbox"]):
            obstacles.append((word["bbox"][1], f"글자 {word['text']!r}"))

    if obstacles:
        nearest_top, description = min(obstacles, key=lambda item: item[0])
        limited_bottom = nearest_top - gap_mm
        if limited_bottom < centred_bottom:
            return left, limited_bottom, f"아래 {description} 회피 (상단 {nearest_top:.1f}mm)"
    return left, centred_bottom, "기준 글자 줄에 세로 중앙 정렬"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Render-measure-place-verify an approved signature or stamp on HWPX."
    )
    parser.add_argument("source", help="Source .hwpx with text already filled")
    parser.add_argument("signature", help="Approved image (.png/.jpg/.jpeg/.bmp)")
    parser.add_argument("--output", help="Output .hwpx; default is <source>_완성본.hwpx")
    parser.add_argument("--report", action="store_true", help="Measure only; do not create output")
    parser.add_argument("--find", action="append", default=[], metavar="TEXT")
    parser.add_argument(
        "--anchor-para",
        metavar="TEXT",
        help="Unique paragraph above the target; a picture cannot move above its anchor",
    )
    parser.add_argument("--width-mm", type=float, default=24.0)
    parser.add_argument("--after-text", metavar="TEXT", help="Start where this rendered text ends")
    parser.add_argument("--target-left-mm", type=float)
    parser.add_argument("--target-bottom-mm", type=float)
    parser.add_argument("--gap-mm", type=float, default=0.4)
    parser.add_argument("--occurrence", choices=("first", "last"), default="last")
    parser.add_argument("--tolerance-mm", type=float, default=0.3)
    parser.add_argument("--page", type=int, default=0, help="0-based page index")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def _cleanup_temp_dir(path: Path) -> None:
    for child in path.iterdir():
        try:
            if child.is_file():
                child.unlink()
        except OSError:
            pass
    try:
        path.rmdir()
    except OSError:
        pass


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    source = Path(args.source).expanduser().resolve()
    signature = Path(args.signature).expanduser().resolve()

    if not source.is_file():
        raise SystemExit(f"원본 파일 없음: {source}")
    if source.suffix.lower() != ".hwpx":
        raise SystemExit("서명·도장 실측 배치는 HWPX만 지원합니다. 원본은 변경하지 않았습니다.")
    if not signature.is_file():
        raise SystemExit(f"이미지 파일 없음: {signature}")
    if args.width_mm <= 0 or args.gap_mm < 0 or args.tolerance_mm < 0:
        raise SystemExit("폭은 0보다 커야 하고 간격·허용 오차는 음수일 수 없습니다.")
    if args.page < 0:
        raise SystemExit("--page는 0 이상이어야 합니다.")

    pixel_width, pixel_height = image_size(signature)
    aspect = pixel_width / pixel_height
    height_mm = args.width_mm / aspect

    if args.report:
        temp_dir = Path(tempfile.mkdtemp(prefix="place_sig_report_"))
        try:
            source_pdf = temp_dir / "source.pdf"
            export_pdf(source, source_pdf)
            images, _, page_rect = read_page(source_pdf, args.page)
            print(
                f"쪽 크기: {page_rect[0]:.1f} x {page_rect[1]:.1f} mm "
                f"(좌표는 쪽 좌상단 기준)\n"
            )
            print("그림:")
            if not images:
                print("  (없음)")
            for image in images:
                bbox = image["bbox"]
                print(
                    f"  {image['px'][0]}x{image['px'][1]}px "
                    f"좌 {bbox[0]:6.1f} 상 {bbox[1]:6.1f} "
                    f"우 {bbox[2]:6.1f} 하 {bbox[3]:6.1f}"
                )
            for needle in args.find:
                print(f"\n{needle!r}:")
                try:
                    import fitz
                except ImportError as exc:  # pragma: no cover
                    raise SystemExit("PyMuPDF가 필요합니다: py -3 -m pip install pymupdf") from exc
                doc = fitz.open(source_pdf)
                try:
                    hits = doc[args.page].search_for(needle)
                finally:
                    doc.close()
                if not hits:
                    print("  (찾지 못함)")
                for hit in hits:
                    bbox = [value * MM_PER_PT for value in hit]
                    print(
                        f"  좌 {bbox[0]:6.1f} 상 {bbox[1]:6.1f} "
                        f"우 {bbox[2]:6.1f} 하 {bbox[3]:6.1f}"
                    )
            print(
                f"\n이미지 {pixel_width}x{pixel_height}px를 폭 {args.width_mm}mm로 넣으면 "
                f"높이 {height_mm:.1f}mm입니다."
            )
            return 0
        finally:
            _cleanup_temp_dir(temp_dir)

    if not args.anchor_para:
        raise SystemExit("--anchor-para가 필요합니다. 목표보다 위에 있는 고유 문단을 지정하세요.")
    explicit_target = args.target_left_mm is not None and args.target_bottom_mm is not None
    partial_target = (args.target_left_mm is None) != (args.target_bottom_mm is None)
    if partial_target:
        raise SystemExit("--target-left-mm와 --target-bottom-mm는 함께 지정해야 합니다.")
    if not explicit_target and not args.after_text:
        raise SystemExit("--after-text 또는 좌·하단 목표 좌표가 필요합니다.")

    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else unique_output_path(source).resolve()
    )
    if output.suffix.lower() != ".hwpx":
        raise SystemExit("출력 파일 확장자는 .hwpx여야 합니다.")
    if output == source:
        raise SystemExit("출력 경로는 원본과 달라야 합니다.")
    if output.exists() and not args.overwrite:
        raise SystemExit(f"기존 출력은 덮어쓰지 않습니다: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="place_sig_"))
    try:
        source_pdf = temp_dir / "source.pdf"
        export_pdf(source, source_pdf)
        baseline_images, _, _ = read_page(source_pdf, args.page)

        def build(destination: Path, horizontal_mm: float, vertical_mm: float) -> None:
            insert_signature(
                source=source,
                signature=signature,
                output=destination,
                anchor="",
                occurrence=args.occurrence,
                width_hwpunit=round(args.width_mm * 7200 / 25.4),
                overwrite=True,
                placement="overlay",
                vert_offset_hwpunit=round(vertical_mm * 7200 / 25.4),
                horz_offset_hwpunit=round(horizontal_mm * 7200 / 25.4),
                anchor_para=args.anchor_para,
            )

        probe = temp_dir / "probe.hwpx"
        probe_pdf = temp_dir / "probe.pdf"
        build(probe, PROBE_HORZ_MM, PROBE_VERT_MM)
        export_pdf(probe, probe_pdf)
        probe_images, words, _ = read_page(probe_pdf, args.page)
        probe_bbox = pick_inserted_image(
            probe_images,
            baseline_images,
            args.width_mm,
            aspect,
            (pixel_width, pixel_height),
        )

        column_origin = probe_bbox[0] - PROBE_HORZ_MM
        paragraph_origin = probe_bbox[1] - PROBE_VERT_MM
        print(
            f"탐침 offset({PROBE_HORZ_MM}, {PROBE_VERT_MM}) -> "
            f"좌 {probe_bbox[0]:.1f} 상 {probe_bbox[1]:.1f} mm"
        )
        print(f"  원점: COLUMN {column_origin:.1f}mm, PARA {paragraph_origin:.1f}mm")

        if explicit_target:
            left = args.target_left_mm
            bottom = args.target_bottom_mm
            reason = "직접 지정"
        else:
            line_bbox = find_phrase(probe_pdf, args.after_text, args.occurrence, args.page)
            left, bottom, reason = derive_target(
                line_bbox,
                probe_images,
                words,
                probe_bbox,
                args.width_mm,
                height_mm,
                args.gap_mm,
            )
            print(
                f"  기준 {args.after_text!r}: 좌 {line_bbox[0]:.1f} 상 {line_bbox[1]:.1f} "
                f"우 {line_bbox[2]:.1f} 하 {line_bbox[3]:.1f} mm"
            )

        top = bottom - height_mm
        print(f"  목표: 좌 {left:.1f}mm, 상 {top:.1f}mm, 하 {bottom:.1f}mm ({reason})")

        horizontal_mm = left - column_origin
        vertical_mm = top - paragraph_origin
        if horizontal_mm < 0:
            raise SystemExit(
                f"가로 오프셋이 음수({horizontal_mm:.1f}mm)입니다. "
                "더 왼쪽 기준의 앵커를 고르세요."
            )
        if vertical_mm < 0:
            raise SystemExit(
                f"세로 오프셋이 음수({vertical_mm:.1f}mm)입니다. "
                "--anchor-para를 더 위쪽 문단으로 바꾸세요."
            )

        verified_candidate = None
        final_error = None
        for attempt in (1, 2):
            candidate = temp_dir / f"candidate{attempt}.hwpx"
            candidate_pdf = temp_dir / f"candidate{attempt}.pdf"
            build(candidate, horizontal_mm, vertical_mm)
            export_pdf(candidate, candidate_pdf)
            rendered_images, _, _ = read_page(candidate_pdf, args.page)
            actual_bbox = pick_inserted_image(
                rendered_images,
                baseline_images,
                args.width_mm,
                aspect,
                (pixel_width, pixel_height),
            )
            delta_x = left - actual_bbox[0]
            delta_y = bottom - actual_bbox[3]
            final_error = max(abs(delta_x), abs(delta_y))
            print(
                f"  {attempt}차: 좌 {actual_bbox[0]:.1f} 상 {actual_bbox[1]:.1f} "
                f"우 {actual_bbox[2]:.1f} 하 {actual_bbox[3]:.1f} mm "
                f"오차 좌 {-delta_x:+.2f} 하 {-delta_y:+.2f}"
            )
            if final_error <= args.tolerance_mm:
                verified_candidate = candidate
                break
            horizontal_mm += delta_x
            vertical_mm += delta_y

        if verified_candidate is None:
            raise SystemExit(
                f"배치 오차가 허용치 {args.tolerance_mm:.2f}mm 안에 들지 않았습니다 "
                f"(최종 {final_error:.2f}mm). 출력하지 않았습니다."
            )
        if output.exists() and not args.overwrite:
            raise SystemExit(f"작업 중 같은 이름의 파일이 생겨 출력하지 않았습니다: {output}")

        pending_fd, pending_name = tempfile.mkstemp(
            prefix=f".{output.stem}_",
            suffix=".pending",
            dir=output.parent,
        )
        os.close(pending_fd)
        pending = Path(pending_name)
        try:
            shutil.copy2(verified_candidate, pending)
            if output.exists() and not args.overwrite:
                raise SystemExit(f"작업 중 같은 이름의 파일이 생겨 출력하지 않았습니다: {output}")
            os.replace(pending, output)
        finally:
            if pending.exists():
                pending.unlink()

        print(f"\n저장: {output}")
        print(f"  방식 overlay(BEHIND_TEXT), 크기 {args.width_mm:.1f} x {height_mm:.1f}mm")
        print(
            f"  앵커 문단 {args.anchor_para!r}, "
            f"horzOffset {horizontal_mm:.1f}mm, vertOffset {vertical_mm:.1f}mm"
        )
        return 0
    finally:
        _cleanup_temp_dir(temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
