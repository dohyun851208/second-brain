#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Place a signature image at an exact position on an HWPX form.

`insert_signature_hwpx.py` writes the picture, but its offsets are relative to
an anchor whose origin cannot be derived reliably from the XML: COLUMN may mean
the page text column or a table cell, PARA depends on which paragraph the run
really sits in, and nested tables defeat regex paragraph matching. Guessing the
origin puts the signature in the wrong place, and nothing in the file reveals
the error.

So this script measures instead. It inserts the picture once at a probe offset,
exports a throwaway PDF through 한컴 COM, reads where the picture actually
landed, solves for the offset that hits the requested position, rebuilds, and
verifies. Two renders, and the result is accurate to a few hundredths of a mm.

The same render also locates form text, so a target can be expressed as "start
where the typed name ends, sitting on that line" instead of a raw coordinate.

Requires pywin32 (한컴 COM) and PyMuPDF.

Examples:
    # look at the form first: where is everything, in mm?
    place_signature.py 신청서.hwpx 서명.png --report --find 홍길동 --find "(서명)"

    # place it: right after the typed name, on that line, clear of what is below
    place_signature.py 신청서.hwpx 서명.png --output 신청서_완성본.hwpx \\
        --anchor-para "4. 위 사항을 준수하겠습니다" --after-text 홍길동 --width-mm 24

    # or give the page coordinates directly
    place_signature.py 신청서.hwpx 서명.png --output 신청서_완성본.hwpx \\
        --anchor-para "소    속 :" --target-left-mm 66.1 --target-bottom-mm 182.6
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from insert_signature_hwpx import image_size, insert_signature, unique_output_path  # noqa: E402

MM_PER_PT = 25.4 / 72
PROBE_HORZ_MM = 100.0
PROBE_VERT_MM = 5.0


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def export_pdf(hwpx: Path, pdf: Path) -> None:
    """Export via 한컴 COM. Read-only for the HWPX: it is opened, never saved."""
    try:
        import win32com.client as win32
    except ImportError:  # pragma: no cover
        raise SystemExit("pywin32가 필요합니다: python -m pip install pywin32")

    hwp = win32.Dispatch("HWPFrame.HwpObject")
    try:
        try:
            hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
        except Exception:
            print("WARN: 보안모듈 등록 실패 — scripts/setup_env.py를 먼저 실행하세요.")
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
        raise SystemExit(f"PDF 내보내기 실패: {pdf}")


def read_page(pdf: Path, page_no: int = 0):
    """Return (images, words, page rect) with every coordinate in millimetres."""
    try:
        import fitz
    except ImportError:  # pragma: no cover
        raise SystemExit("PyMuPDF가 필요합니다: python -m pip install pymupdf")

    doc = fitz.open(pdf)
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
    doc.close()
    return images, words, rect


def find_phrase(pdf: Path, needle: str, occurrence: str, page_no: int = 0):
    """Locate `needle` on the page. Returns its bbox in millimetres."""
    import fitz

    doc = fitz.open(pdf)
    hits = doc[page_no].search_for(needle)
    doc.close()
    if not hits:
        raise SystemExit(f"본문에서 찾지 못했습니다: {needle!r}")
    hit = hits[0] if occurrence == "first" else hits[-1]
    return tuple(v * MM_PER_PT for v in hit)


def pick_signature(images, want_width_mm: float, aspect: float):
    """Find the inserted picture among the form's own images.

    Matched on rendered size rather than pixel dimensions: the rasteriser may
    report a pixel height one off from the source file, but the drawn width is
    exactly what was asked for.
    """
    best, best_err = None, None
    for im in images:
        x0, y0, x1, y1 = im["bbox"]
        w, h = x1 - x0, y1 - y0
        if h <= 0:
            continue
        err = abs(w - want_width_mm)
        if err > 0.6 or abs((w / h) - aspect) > 0.03 * aspect:
            continue
        if best_err is None or err < best_err:
            best, best_err = im, err
    if best is None:
        raise SystemExit(
            f"렌더링된 쪽에서 삽입한 서명을 식별하지 못했습니다 "
            f"(폭 {want_width_mm}mm, 비율 {aspect:.2f} 기준)."
        )
    return best["bbox"]


# --------------------------------------------------------------------------
# target
# --------------------------------------------------------------------------

def derive_target(line_bbox, images, words, sig_bbox, width_mm, height_mm, gap_mm):
    """Work out where the signature should sit, from the form's own layout.

    Mirrors how the signature is placed by hand: it starts where the typed name
    ends and is centred on that line. When something sits directly underneath —
    another signer's line, an existing seal — it is lifted just clear of it
    instead, because a signature must never cover another person's mark.
    """
    lx0, ly0, lx1, ly1 = line_bbox
    left = lx1
    right = left + width_mm
    centred_bottom = (ly0 + ly1) / 2 + height_mm / 2

    def overlaps(bbox):
        return not (bbox[2] <= left + 0.2 or bbox[0] >= right - 0.2)

    obstacles = []
    for im in images:
        if im["bbox"] == sig_bbox:
            continue
        if im["bbox"][1] >= ly1 - 0.2 and overlaps(im["bbox"]):
            obstacles.append((im["bbox"][1], f"그림 {im['px'][0]}x{im['px'][1]}px"))
    for wd in words:
        if wd["bbox"][1] >= ly1 - 0.2 and overlaps(wd["bbox"]):
            obstacles.append((wd["bbox"][1], f"글자 {wd['text']!r}"))

    if obstacles:
        top_of_nearest, what = min(obstacles, key=lambda o: o[0])
        limited_bottom = top_of_nearest - gap_mm
        if limited_bottom < centred_bottom:
            return left, limited_bottom, f"아래 {what} 회피 (상단 {top_of_nearest:.1f}mm)"
    return left, centred_bottom, "이름 줄에 세로 중앙 정렬"


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Place a signature on an HWPX form by measuring the rendered page.")
    p.add_argument("source", help="Source .hwpx (text already filled in)")
    p.add_argument("signature", help="Signature image (.png/.jpg/.bmp)")
    p.add_argument("--output", help="Output .hwpx. Defaults to <source>_완성본.hwpx")
    p.add_argument("--report", action="store_true",
                   help="Only measure the form and print its geometry in mm.")
    p.add_argument("--find", action="append", default=[], metavar="TEXT",
                   help="Report mode: also locate this text. Repeatable.")
    p.add_argument("--anchor-para", metavar="TEXT",
                   help="Paragraph to anchor to. Must sit ABOVE the target: a picture "
                        "cannot be offset above its anchor paragraph.")
    p.add_argument("--width-mm", type=float, default=24.0, help="Displayed width (default 24).")
    p.add_argument("--after-text", metavar="TEXT",
                   help="Target starts where this text ends, on that text's line.")
    p.add_argument("--target-left-mm", type=float, help="Explicit target left edge, from page left.")
    p.add_argument("--target-bottom-mm", type=float, help="Explicit target bottom, from page top.")
    p.add_argument("--gap-mm", type=float, default=0.4,
                   help="Clearance kept above whatever sits below (default 0.4).")
    p.add_argument("--occurrence", choices=("first", "last"), default="last",
                   help="Which occurrence of --after-text / --anchor-para to use.")
    p.add_argument("--tolerance-mm", type=float, default=0.3,
                   help="Accepted placement error (default 0.3).")
    p.add_argument("--page", type=int, default=0, help="0-based page index (default 0).")
    p.add_argument("--overwrite", action="store_true", help="Overwrite --output if present.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    source, signature = Path(args.source), Path(args.signature)
    for f in (source, signature):
        if not f.is_file():
            raise SystemExit(f"파일 없음: {f}")

    px_w, px_h = image_size(signature)
    aspect = px_w / px_h
    height_mm = args.width_mm / aspect

    tmp = Path(tempfile.mkdtemp(prefix="place_sig_"))
    try:
        # ---------- report ----------
        if args.report:
            pdf = tmp / "report.pdf"
            export_pdf(source, pdf)
            images, words, rect = read_page(pdf, args.page)
            print(f"쪽 크기: {rect[0]:.1f} x {rect[1]:.1f} mm   (좌표는 쪽 좌상단 기준)\n")
            print("그림:")
            for im in images:
                b = im["bbox"]
                print(f"  {im['px'][0]}x{im['px'][1]}px   좌 {b[0]:6.1f}  상 {b[1]:6.1f}  "
                      f"우 {b[2]:6.1f}  하 {b[3]:6.1f}")
            if not images:
                print("  (없음)")
            for needle in args.find:
                print(f"\n{needle!r}:")
                import fitz
                doc = fitz.open(pdf)
                for h in doc[args.page].search_for(needle):
                    b = [v * MM_PER_PT for v in h]
                    print(f"  좌 {b[0]:6.1f}  상 {b[1]:6.1f}  우 {b[2]:6.1f}  하 {b[3]:6.1f}")
                doc.close()
            print(f"\n서명 {px_w}x{px_h}px를 폭 {args.width_mm}mm로 넣으면 "
                  f"높이 {height_mm:.1f}mm입니다.")
            return 0

        # ---------- placement ----------
        if not args.anchor_para:
            raise SystemExit("--anchor-para 가 필요합니다 (목표보다 위에 있는 문단의 텍스트).")
        explicit = args.target_left_mm is not None and args.target_bottom_mm is not None
        if not explicit and not args.after_text:
            raise SystemExit("--after-text 또는 --target-left-mm/--target-bottom-mm 이 필요합니다.")

        output = Path(args.output) if args.output else unique_output_path(source)

        def build(dst, horz, vert):
            insert_signature(
                source=source, signature=signature, output=dst,
                anchor="", occurrence=args.occurrence,
                width_hwpunit=round(args.width_mm * 7200 / 25.4), overwrite=True,
                placement="overlay",
                vert_offset_hwpunit=round(vert * 7200 / 25.4),
                horz_offset_hwpunit=round(horz * 7200 / 25.4),
                anchor_para=args.anchor_para,
            )

        # probe: one build at a known offset reveals both origins
        probe = tmp / "probe.hwpx"
        probe_pdf = tmp / "probe.pdf"
        build(probe, PROBE_HORZ_MM, PROBE_VERT_MM)
        export_pdf(probe, probe_pdf)
        images, words, _ = read_page(probe_pdf, args.page)
        sig_bbox = pick_signature(images, args.width_mm, aspect)

        col_origin = sig_bbox[0] - PROBE_HORZ_MM
        para_origin = sig_bbox[1] - PROBE_VERT_MM
        print(f"탐침 offset({PROBE_HORZ_MM}, {PROBE_VERT_MM}) -> "
              f"좌 {sig_bbox[0]:.1f} 상 {sig_bbox[1]:.1f} mm")
        print(f"  원점: COLUMN {col_origin:.1f}mm, PARA {para_origin:.1f}mm")

        if explicit:
            left, bottom, why = args.target_left_mm, args.target_bottom_mm, "직접 지정"
        else:
            line = find_phrase(probe_pdf, args.after_text, args.occurrence, args.page)
            left, bottom, why = derive_target(
                line, images, words, sig_bbox, args.width_mm, height_mm, args.gap_mm)
            print(f"  기준 {args.after_text!r}: 좌 {line[0]:.1f} 상 {line[1]:.1f} "
                  f"우 {line[2]:.1f} 하 {line[3]:.1f} mm")
        top = bottom - height_mm
        print(f"  목표: 좌 {left:.1f}mm, 상 {top:.1f}mm, 하 {bottom:.1f}mm  ({why})")

        horz, vert = left - col_origin, top - para_origin
        if vert < 0:
            raise SystemExit(
                f"세로 오프셋이 음수({vert:.1f}mm)입니다. 그림은 앵커 문단 위로 올라가지 못하고 "
                f"조용히 문단 상단에 붙습니다. --anchor-para 를 더 위쪽 문단으로 바꾸세요.")

        for attempt in (1, 2):
            build(output, horz, vert)
            out_pdf = tmp / f"out{attempt}.pdf"
            export_pdf(output, out_pdf)
            got = pick_signature(read_page(out_pdf, args.page)[0], args.width_mm, aspect)
            dx, dy = left - got[0], bottom - got[3]
            print(f"  {attempt}차: 좌 {got[0]:.1f} 상 {got[1]:.1f} 우 {got[2]:.1f} 하 {got[3]:.1f} mm"
                  f"   오차 좌 {-dx:+.2f} 하 {-dy:+.2f}")
            if max(abs(dx), abs(dy)) <= args.tolerance_mm:
                break
            horz, vert = horz + dx, vert + dy

        print(f"\n저장: {output}")
        print(f"  방식 overlay(BEHIND_TEXT), 크기 {args.width_mm} x {height_mm:.1f}mm")
        print(f"  앵커 문단 {args.anchor_para!r}, horzOffset {horz:.1f}mm, vertOffset {vert:.1f}mm")
        return 0
    finally:
        for f in tmp.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
