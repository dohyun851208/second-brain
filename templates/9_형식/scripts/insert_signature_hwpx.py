#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Insert a handwritten signature image into an HWPX form.

This script edits the HWPX ZIP/XML package directly. It avoids COM
InsertPicture and avoids fragile PowerShell `python -c` XML string quoting.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


HWPUNIT_PER_MM = 7200 / 25.4
# HWPUNIT is 1/7200 inch and 한글 treats embedded bitmaps as 96 dpi, so one
# source pixel is 7200/96 = 75 HWPUNIT in the image's own coordinate space.
HWPUNIT_PER_PX = 75
RUN_RE = re.compile(r"<hp:run\b.*?</hp:run>|<hp:run\b[^>]*/>", re.DOTALL)
PARA_RE = re.compile(r"<hp:p\b.*?</hp:p>", re.DOTALL)


def visible_text(xml: str) -> str:
    """Return human-visible text from a small HWPX XML fragment."""
    text = re.sub(r"<hp:tab\b[^>]*/>", " ", xml)
    text = re.sub(r"<hp:lineBreak\b[^>]*/>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i < len(data):
            while i < len(data) and data[i] == 0xFF:
                i += 1
            if i >= len(data):
                break
            marker = data[i]
            i += 1
            if marker in (0xD8, 0xD9):
                continue
            if i + 2 > len(data):
                break
            length = struct.unpack(">H", data[i:i + 2])[0]
            if marker in range(0xC0, 0xC4) or marker in range(0xC5, 0xC8) or marker in range(0xC9, 0xCC) or marker in range(0xCD, 0xD0):
                if i + 7 <= len(data):
                    height, width = struct.unpack(">HH", data[i + 3:i + 7])
                    return width, height
            i += length
    raise ValueError(f"Unsupported image format or invalid image: {path}")


def unique_output_path(source: Path) -> Path:
    out_dir = source.parent
    candidate = out_dir / f"{source.stem}_완성본{source.suffix}"
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        candidate = out_dir / f"{source.stem}_완성본{n}{source.suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def unique_manifest_id(content_hpf: str, base: str = "signature") -> str:
    used = set(re.findall(r"\bid=(['\"])(.*?)\1", content_hpf))
    used_ids = {value for _, value in used}
    if base not in used_ids:
        return base
    n = 2
    while f"{base}{n}" in used_ids:
        n += 1
    return f"{base}{n}"


def unique_bindata_name(names: set[str], base: str = "signature", ext: str = ".png") -> str:
    candidate = f"BinData/{base}{ext}"
    if candidate not in names:
        return candidate
    n = 2
    while True:
        candidate = f"BinData/{base}{n}{ext}"
        if candidate not in names:
            return candidate
        n += 1


def unique_number(section: str, start: int) -> int:
    n = start
    while (
        f'id="{n}"' in section
        or f"id='{n}'" in section
        or f'instid="{n}"' in section
        or f"instid='{n}'" in section
    ):
        n += 1
    return n


def attr_value(xml: str, name: str, default: str) -> str:
    match = re.search(rf"\b{name}=(['\"])(.*?)\1", xml)
    return match.group(2) if match else default


def char_pr_height_pt(header_xml: str, char_pr_id: str) -> float | None:
    """Return the font size in points for a charPr id, or None if not found."""
    match = re.search(rf'<hh:charPr\b[^>]*\bid="{char_pr_id}"[^>]*\bheight="(\d+)"', header_xml)
    if not match:
        return None
    return int(match.group(1)) / 100.0


def estimate_text_width(text: str, pt: float) -> int:
    """Rough advance width of `text` in HWPUNIT at `pt` size.

    Hangul/CJK glyphs occupy about one em; ASCII and spaces about half.
    Only used to place an overlay signature, which the caller can nudge
    with --horz-offset-mm, so an approximation is enough.
    """
    em = pt * 100.0
    width = 0.0
    for ch in text:
        if ch == "\t":
            width += em * 4
        elif ord(ch) > 0x2000:
            width += em
        else:
            width += em * 0.5
    return round(width)


def make_pic_run(
    binary_id: str,
    char_pr: str,
    width: int,
    height: int,
    pic_id: int,
    inst_id: int,
    img_px: tuple[int, int],
    placement: str = "inline",
    vert_offset: int = 0,
    horz_offset: int = 0,
    z_order: int = 0,
) -> str:
    """Build the <hp:run> that carries the picture.

    HWPX keeps three different sizes and confusing them silently crops the image:

    - ``orgSz`` / ``imgRect`` / ``imgClip`` live in the SOURCE image's own
      coordinate space (pixels x 75, i.e. 96 dpi). ``imgClip`` is the region cut
      OUT of that source, so it must span the whole image.
    - ``curSz`` / ``sz`` are the size the picture is drawn at on the page.
    - ``scaMatrix`` carries the ratio between the two.

    Writing the display size into ``imgClip`` crops the source down to that
    fraction of itself and stretches the fragment to fill the frame — a 20mm
    signature off a 212px image then shows only its leftmost third.
    """
    px_w, px_h = img_px
    nat_w, nat_h = px_w * HWPUNIT_PER_PX, px_h * HWPUNIT_PER_PX
    scale = width / nat_w if nat_w else 1.0
    if placement == "overlay":
        # Float the signature behind the text so the line height is unchanged
        # and the form's own "(서명)" marker stays readable on top of it.
        # Horizontal position is measured from the column (table cell) edge, not
        # the paragraph, so paragraph indentation cannot shift it.
        text_wrap = "BEHIND_TEXT"
        pos = (
            f'<hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
            f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" '
            f'vertOffset="{vert_offset}" horzOffset="{horz_offset}"/>'
        )
    else:
        text_wrap = "TOP_AND_BOTTOM"
        pos = (
            f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
            f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" '
            f'vertOffset="0" horzOffset="0"/>'
        )
    return (
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:pic id="{pic_id}" zOrder="{z_order}" numberingType="PICTURE" '
        f'textWrap="{text_wrap}" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" '
        f'href="" groupLevel="0" instid="{inst_id}" reverse="0">'
        f'<hp:offset x="0" y="0"/>'
        f'<hp:orgSz width="{nat_w}" height="{nat_h}"/>'
        f'<hp:curSz width="{width}" height="{height}"/>'
        f'<hp:flip horizontal="0" vertical="0"/>'
        f'<hp:rotationInfo angle="0"/>'
        f'<hp:renderingInfo>'
        f'<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'<hc:scaMatrix e1="{scale:.6f}" e2="0" e3="0" e4="0" e5="{scale:.6f}" e6="0"/>'
        f'<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'</hp:renderingInfo>'
        f'<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="{nat_w}" y="0"/>'
        f'<hc:pt2 x="{nat_w}" y="{nat_h}"/><hc:pt3 x="0" y="{nat_h}"/></hp:imgRect>'
        f'<hp:imgClip left="0" right="{nat_w}" top="0" bottom="{nat_h}"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hc:img binaryItemIDRef="{binary_id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
        f'<hp:effects/>'
        f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
        + pos +
        f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        f'</hp:pic><hp:t/></hp:run>'
    )


def find_insert_point(section: str, anchor: str, occurrence: str) -> tuple[int, str, str, str]:
    """Locate where to splice the picture run.

    Returns (absolute offset, charPrIDRef, paragraph text, text before the pic).
    The last item is the visible text preceding the insertion point inside the
    paragraph; overlay placement uses it to estimate the horizontal offset.
    """
    matches: list[tuple[re.Match[str], str]] = []
    for para_match in PARA_RE.finditer(section):
        para_xml = para_match.group(0)
        if anchor in visible_text(para_xml):
            matches.append((para_match, para_xml))
    if not matches:
        raise ValueError(f"Anchor text not found in any paragraph: {anchor}")

    para_match, para_xml = matches[0] if occurrence == "first" else matches[-1]
    run_matches = list(RUN_RE.finditer(para_xml))
    if not run_matches:
        raise ValueError("Target paragraph has no hp:run element.")

    anchor_runs = [run for run in run_matches if anchor in visible_text(run.group(0))]
    if anchor_runs:
        target_run = anchor_runs[-1]
    else:
        nonempty_runs = [run for run in run_matches if visible_text(run.group(0)).strip()]
        target_run = nonempty_runs[-1] if nonempty_runs else run_matches[-1]

    run_xml = target_run.group(0)
    char_pr = attr_value(run_xml, "charPrIDRef", "13")
    absolute_insert_pos = para_match.start() + target_run.end()
    text_before = visible_text(para_xml[:target_run.end()])
    return absolute_insert_pos, char_pr, visible_text(para_xml).strip(), text_before


def find_para_anchor(section: str, para_text: str, occurrence: str) -> tuple[int, str]:
    """Anchor the picture to the paragraph containing `para_text`.

    Returns (offset of that paragraph's first run, charPrIDRef). This mirrors
    what 한글 does when a picture is inserted with the cursor on a line and then
    dragged: the anchor stays on the paragraph and only the offsets change. It
    leaves the paragraph's runs untouched, so no run splitting is needed.
    """
    matches = [m for m in PARA_RE.finditer(section) if para_text in visible_text(m.group(0))]
    if not matches:
        raise ValueError(f"Anchor paragraph not found: {para_text}")
    para_match = matches[0] if occurrence == "first" else matches[-1]
    para_xml = para_match.group(0)

    run_match = RUN_RE.search(para_xml)
    if not run_match:
        raise ValueError("Anchor paragraph has no hp:run element.")
    char_pr = attr_value(run_match.group(0), "charPrIDRef", "13")
    return para_match.start() + run_match.start(), char_pr


def max_z_order(section: str) -> int:
    values = [int(v) for v in re.findall(r'\bzOrder="(-?\d+)"', section)]
    return max(values) if values else 0


def validate_xml_members(hwpx_path: Path) -> None:
    with zipfile.ZipFile(hwpx_path, "r") as zf:
        names = zf.namelist()
        if not names or names[0] != "mimetype":
            raise ValueError("mimetype is not the first ZIP entry.")
        if zf.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            raise ValueError("mimetype must be stored without compression.")
        for required in ("Contents/content.hpf", "Contents/header.xml", "Contents/section0.xml"):
            if required not in names:
                raise ValueError(f"Missing required HWPX member: {required}")
        for name in names:
            if name.endswith(".xml") or name.endswith(".hpf"):
                ElementTree.fromstring(zf.read(name))


def insert_signature(
    source: Path,
    signature: Path,
    output: Path,
    anchor: str,
    occurrence: str,
    width_hwpunit: int,
    overwrite: bool,
    placement: str = "inline",
    vert_offset_hwpunit: int | None = None,
    horz_offset_hwpunit: int | None = None,
    fit_line: float | None = None,
    anchor_para: str | None = None,
) -> tuple[Path, str, str, int, int]:
    source = source.resolve()
    signature = signature.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("Output path must be different from source path.")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists. Use --overwrite or choose another path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    img_w, img_h = image_size(signature)
    height_hwpunit = round(width_hwpunit * img_h / img_w)

    with zipfile.ZipFile(source, "r") as zin:
        names = set(zin.namelist())
        section = zin.read("Contents/section0.xml").decode("utf-8")
        content_hpf = zin.read("Contents/content.hpf").decode("utf-8")
        header_xml = zin.read("Contents/header.xml").decode("utf-8")

        binary_id = unique_manifest_id(content_hpf)
        ext = signature.suffix.lower() or ".png"
        media = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
        }.get(ext)
        if not media:
            raise ValueError(f"Unsupported signature image extension: {ext}")
        bindata_name = unique_bindata_name(names, "signature", ext)

        if anchor_para:
            insert_pos, char_pr = find_para_anchor(section, anchor_para, occurrence)
            matched_text, text_before = anchor_para, ""
        else:
            insert_pos, char_pr, matched_text, text_before = find_insert_point(section, anchor, occurrence)

        # Line height of the anchored text decides whether the signature fits.
        pt = char_pr_height_pt(header_xml, char_pr) or 10.0
        line_h = round(pt * 100)

        if fit_line is not None:
            height_hwpunit = round(line_h * fit_line)
            width_hwpunit = round(height_hwpunit * img_w / img_h)
            print(f"fit_line: 글자 {pt}pt 기준으로 축소 -> {width_hwpunit}x{height_hwpunit} HWPUNIT")

        ratio = height_hwpunit / line_h
        if placement == "inline" and ratio > 1.2:
            remedy = "--overlay 로 띄우거나 --fit-line 값을 낮추세요." if fit_line is not None \
                else "--overlay 또는 --fit-line 을 고려하세요."
            print(
                f"WARN: 서명 높이가 글자 높이의 {ratio:.1f}배입니다. inline 배치는 줄 높이를 밀어내"
                f" 1쪽 고정 양식이 다음 쪽으로 넘칠 수 있습니다. {remedy}"
            )

        if placement == "overlay":
            if horz_offset_hwpunit is None:
                if anchor_para:
                    raise ValueError(
                        "--anchor-para 사용 시에는 --horz-offset-mm 을 함께 주세요. "
                        "앵커 문단만으로는 가로 위치를 알 수 없습니다."
                    )
                # Estimated from the text preceding the signature. Roughly 10%
                # low against 한글's own layout, so scale it up a little.
                horz_offset_hwpunit = round(estimate_text_width(text_before, pt) * 1.1)
                print(f"NOTE: 가로 위치는 추정값입니다. 어긋나면 --horz-offset-mm 으로 직접 주세요.")
            if vert_offset_hwpunit is None:
                # Hang from the top of the anchored line: a signature sits on the
                # name line, never above it. Negative values would ride up into
                # the previous line.
                vert_offset_hwpunit = 0
            print(
                f"overlay: BEHIND_TEXT, 줄 높이 유지. 위치 "
                f"가로 {horz_offset_hwpunit/HWPUNIT_PER_MM:.1f}mm (단 좌측 기준), "
                f"세로 {vert_offset_hwpunit/HWPUNIT_PER_MM:+.1f}mm (앵커 문단 상단 기준)"
            )
        else:
            horz_offset_hwpunit = horz_offset_hwpunit or 0
            vert_offset_hwpunit = vert_offset_hwpunit or 0

        pic_id = unique_number(section, 900000001)
        inst_id = unique_number(section, pic_id + 1)
        pic_xml = make_pic_run(
            binary_id, char_pr, width_hwpunit, height_hwpunit, pic_id, inst_id,
            img_px=(img_w, img_h),
            placement=placement,
            vert_offset=vert_offset_hwpunit,
            horz_offset=horz_offset_hwpunit,
            z_order=max_z_order(section) + 1 if placement == "overlay" else 0,
        )
        section_new = section[:insert_pos] + pic_xml + section[insert_pos:]

        manifest_item = (
            f'<opf:item id="{binary_id}" href="{bindata_name}" '
            f'media-type="{media}" isEmbeded="1"/>'
        )
        if "</opf:manifest>" not in content_hpf:
            raise ValueError("Cannot find </opf:manifest> in Contents/content.hpf.")
        content_hpf_new = content_hpf.replace("</opf:manifest>", manifest_item + "</opf:manifest>", 1)

        tmp = output.with_suffix(output.suffix + ".tmp")
        try:
            with zipfile.ZipFile(tmp, "w") as zout:
                for info in zin.infolist():
                    data = zin.read(info.filename)
                    if info.filename == "Contents/section0.xml":
                        data = section_new.encode("utf-8")
                    elif info.filename == "Contents/content.hpf":
                        data = content_hpf_new.encode("utf-8")

                    zi = zipfile.ZipInfo(info.filename, info.date_time)
                    zi.comment = info.comment
                    zi.extra = info.extra
                    zi.internal_attr = info.internal_attr
                    zi.external_attr = info.external_attr
                    zi.create_system = info.create_system
                    zi.compress_type = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
                    zout.writestr(zi, data)

                img_info = zipfile.ZipInfo(bindata_name)
                img_info.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(img_info, signature.read_bytes())

            validate_xml_members(tmp)
            os.replace(tmp, output)
        finally:
            if tmp.exists():
                tmp.unlink()

    return output, binary_id, bindata_name, width_hwpunit, height_hwpunit


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Insert a signature image into an HWPX form.")
    parser.add_argument("source", help="Source .hwpx file")
    parser.add_argument("signature", help="Signature image file (.png/.jpg/.bmp)")
    parser.add_argument("--output", help="Output .hwpx path. Defaults to source folder with _완성본 suffix.")
    parser.add_argument("--name", help="Name to anchor after, e.g. 홍길동 -> '성명 : 홍길동'")
    parser.add_argument("--anchor", help="Exact paragraph text anchor. Defaults to '성명 : <name>' or '성명 :'.")
    parser.add_argument("--occurrence", choices=("first", "last"), default="last", help="Which matching paragraph to use.")
    parser.add_argument("--width-mm", type=float, default=25.0, help="Displayed signature width in millimeters.")
    parser.add_argument("--width-hwpunit", type=int, help="Displayed signature width in HWPUNIT. Overrides --width-mm.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite --output if it already exists.")
    parser.add_argument(
        "--overlay", action="store_true",
        help="Float the signature above the text instead of inserting it as a character. "
             "Keeps the line height unchanged, so single-page fixed forms do not overflow.",
    )
    parser.add_argument(
        "--fit-line", type=float, nargs="?", const=1.0, metavar="FACTOR",
        help="Scale the signature so its height is FACTOR x the anchored line height (default 1.0).",
    )
    parser.add_argument(
        "--anchor-para", metavar="TEXT",
        help="Overlay only: anchor the picture to the paragraph containing TEXT and position it "
             "by absolute offsets, leaving every run untouched. Use the first line of the "
             "signature block (e.g. '소    속 :'). Requires --horz-offset-mm.",
    )
    parser.add_argument("--vert-offset-mm", type=float, help="Overlay only: vertical offset from the anchor paragraph top, in mm. Positive is downward.")
    parser.add_argument("--horz-offset-mm", type=float, help="Overlay only: horizontal position from the column (cell) left edge, in mm.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    source = Path(args.source)
    signature = Path(args.signature)
    if not source.is_file():
        raise FileNotFoundError(source)
    if not signature.is_file():
        raise FileNotFoundError(signature)

    anchor = args.anchor or (f"성명 : {args.name}" if args.name else "성명 :")
    output = Path(args.output) if args.output else unique_output_path(source)
    width_hwpunit = args.width_hwpunit or round(args.width_mm * HWPUNIT_PER_MM)

    result, binary_id, bindata_name, width, height = insert_signature(
        source=source,
        signature=signature,
        output=output,
        anchor=anchor,
        occurrence=args.occurrence,
        width_hwpunit=width_hwpunit,
        overwrite=args.overwrite,
        placement="overlay" if args.overlay else "inline",
        vert_offset_hwpunit=(round(args.vert_offset_mm * HWPUNIT_PER_MM)
                             if args.vert_offset_mm is not None else None),
        horz_offset_hwpunit=(round(args.horz_offset_mm * HWPUNIT_PER_MM)
                             if args.horz_offset_mm is not None else None),
        fit_line=args.fit_line,
        anchor_para=args.anchor_para,
    )
    print(f"placement={'overlay' if args.overlay else 'inline'}")
    print(f"output={result}")
    print(f"anchor={anchor}")
    print(f"binary_id={binary_id}")
    print(f"bindata={bindata_name}")
    print(f"size_hwpunit={width}x{height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
