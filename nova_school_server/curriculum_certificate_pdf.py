from __future__ import annotations

import hashlib
import math
import unicodedata
import zlib
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - optional runtime enhancement
    Image = None
    ImageOps = None


PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0


def _normalize_text(value: str) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    replacements = {
        "–": "-",
        "—": "-",
        "•": "-",
        "…": "...",
        "„": '"',
        "“": '"',
        "”": '"',
        "’": "'",
        "‚": "'",
        "`": "'",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    try:
        text.encode("cp1252")
        return text
    except UnicodeEncodeError:
        return unicodedata.normalize("NFKD", text).encode("cp1252", "ignore").decode("cp1252") or "?"


def _pdf_string(value: str) -> bytes:
    encoded = _normalize_text(value).encode("cp1252", "replace")
    encoded = encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return b"(" + encoded + b")"


def _rgb(r: float, g: float, b: float) -> bytes:
    return f"{r:.3f} {g:.3f} {b:.3f}".encode("ascii")


def _estimate_width(text: str, font_size: float) -> float:
    return len(_normalize_text(text)) * font_size * 0.53


def _text_command(
    x: float,
    y: float,
    text: str,
    *,
    font: str = "F2",
    size: float = 12,
    color: tuple[float, float, float] = (0.10, 0.13, 0.15),
) -> bytes:
    return (
        b"BT "
        + _rgb(*color)
        + b" rg /"
        + font.encode("ascii")
        + b" "
        + f"{size:.2f}".encode("ascii")
        + b" Tf 1 0 0 1 "
        + f"{x:.2f} {y:.2f}".encode("ascii")
        + b" Tm "
        + _pdf_string(text)
        + b" Tj ET\n"
    )


def _centered_text_command(
    y: float,
    text: str,
    *,
    font: str = "F2",
    size: float = 12,
    color: tuple[float, float, float] = (0.10, 0.13, 0.15),
) -> bytes:
    width = _estimate_width(text, size)
    x = max(48.0, (PAGE_WIDTH - width) / 2.0)
    return _text_command(x, y, text, font=font, size=size, color=color)


def _rect_command(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: tuple[float, float, float] | None = None,
    stroke: tuple[float, float, float] | None = None,
    line_width: float = 1.0,
) -> bytes:
    parts: list[bytes] = [b"q "]
    if fill is not None:
        parts.append(_rgb(*fill) + b" rg ")
    if stroke is not None:
        parts.append(_rgb(*stroke) + b" RG ")
        parts.append(f"{line_width:.2f}".encode("ascii") + b" w ")
    parts.append(f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re ".encode("ascii"))
    if fill is not None and stroke is not None:
        parts.append(b"B ")
    elif fill is not None:
        parts.append(b"f ")
    else:
        parts.append(b"S ")
    parts.append(b"Q\n")
    return b"".join(parts)


def _line_command(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: tuple[float, float, float] = (0.10, 0.13, 0.15),
    line_width: float = 1.0,
) -> bytes:
    return (
        b"q "
        + _rgb(*color)
        + b" RG "
        + f"{line_width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q\n".encode("ascii")
    )


def _image_draw_command(x: float, y: float, width: float, height: float, resource_name: str) -> bytes:
    return f"q {width:.2f} 0 0 {height:.2f} {x:.2f} {y:.2f} cm /{resource_name} Do Q\n".encode("ascii")


def _format_date(timestamp: float) -> str:
    return datetime.fromtimestamp(float(timestamp or 0.0)).strftime("%d.%m.%Y")


def _hex_to_rgb(value: str, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return tuple(int(text[index:index + 2], 16) / 255.0 for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return fallback


def _initials(value: str) -> str:
    parts = [part for part in _normalize_text(value).split() if part]
    if not parts:
        return "NS"
    return "".join(part[0].upper() for part in parts[:3])[:3]


def _wrap_text(text: str, *, max_chars: int) -> list[str]:
    words = _normalize_text(text).split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _load_rgb_image(path: str, *, max_width: int, max_height: int) -> dict[str, object] | None:
    if Image is None or not path:
        return None
    target = Path(path)
    if not target.exists() or not target.is_file():
        return None
    try:
        with Image.open(target) as image:
            if ImageOps is not None:
                image = ImageOps.exif_transpose(image)
            if image.mode not in {"RGB", "L"}:
                image = image.convert("RGBA")
                background = Image.new("RGBA", image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, image).convert("RGB")
            elif image.mode == "L":
                image = image.convert("RGB")
            scale = min(max_width / image.width, max_height / image.height, 1.0)
            if scale < 1.0:
                image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.LANCZOS)
            raw = image.tobytes()
            return {
                "width": image.width,
                "height": image.height,
                "stream": zlib.compress(raw),
            }
    except Exception:
        return None


def _build_verification_matrix(seed: str) -> dict[str, object] | None:
    if Image is None:
        return None
    size = 29
    image = Image.new("RGB", (size, size), (255, 255, 255))
    digest = hashlib.sha256(seed.encode("utf-8")).digest()

    def bit(index: int) -> int:
        data = digest[index % len(digest)]
        return (data >> (index % 8)) & 1

    def draw_finder(origin_x: int, origin_y: int) -> None:
        for y in range(7):
            for x in range(7):
                at_border = x in {0, 6} or y in {0, 6}
                inner = 2 <= x <= 4 and 2 <= y <= 4
                image.putpixel((origin_x + x, origin_y + y), (0, 0, 0) if at_border or inner else (255, 255, 255))

    draw_finder(1, 1)
    draw_finder(size - 8, 1)
    draw_finder(1, size - 8)

    protected = set()
    for start_x, start_y in [(1, 1), (size - 8, 1), (1, size - 8)]:
        for y in range(start_y - 1, start_y + 8):
            for x in range(start_x - 1, start_x + 8):
                if 0 <= x < size and 0 <= y < size:
                    protected.add((x, y))

    cursor = 0
    for y in range(size):
        for x in range(size):
            if (x, y) in protected:
                continue
            image.putpixel((x, y), (0, 0, 0) if bit(cursor) else (255, 255, 255))
            cursor += 1

    image = image.resize((116, 116), Image.NEAREST)
    return {
        "width": image.width,
        "height": image.height,
        "stream": zlib.compress(image.tobytes()),
    }


def build_curriculum_certificate_pdf(
    *,
    school_name: str,
    student_name: str,
    course_title: str,
    certificate_title: str,
    subject_label: str = "",
    theme: dict[str, object] | None = None,
    score: float,
    max_score: float,
    issued_at: float,
    certificate_id: str,
    verification_url: str = "",
    signatory_name: str = "",
    signatory_title: str = "",
    logo_path: str = "",
) -> bytes:
    theme = dict(theme or {})
    accent = _hex_to_rgb(str(theme.get("accent") or ""), (0.07, 0.43, 0.40))
    accent_dark = _hex_to_rgb(str(theme.get("accent_dark") or ""), (0.05, 0.30, 0.29))
    warm = _hex_to_rgb(str(theme.get("warm") or ""), (0.56, 0.25, 0.18))
    ink = (0.11, 0.13, 0.15)
    muted = (0.35, 0.42, 0.43)
    paper = _hex_to_rgb(str(theme.get("paper") or ""), (0.985, 0.972, 0.940))

    score_text = f"{score:.0f} von {max_score:.0f} Punkten" if math.isclose(score, round(score)) and math.isclose(max_score, round(max_score)) else f"{score:.2f} von {max_score:.2f} Punkten"
    date_text = _format_date(issued_at)
    signatory_name = _normalize_text(signatory_name) or "Fachlehrkraft / Schule"
    signatory_title = _normalize_text(signatory_title) or "Freigebende Stelle"
    verification_url = _normalize_text(verification_url)
    subject_label = _normalize_text(subject_label) or _normalize_text(str(theme.get("label") or ""))

    logo = _load_rgb_image(logo_path, max_width=360, max_height=180)
    verification_matrix = _build_verification_matrix(f"{certificate_id}|{verification_url}")

    stream_parts: list[bytes] = [
        _rect_command(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=paper),
        _rect_command(28, 28, PAGE_WIDTH - 56, PAGE_HEIGHT - 56, stroke=accent, line_width=2.2),
        _rect_command(44, PAGE_HEIGHT - 134, PAGE_WIDTH - 88, 74, fill=accent),
        _line_command(70, PAGE_HEIGHT - 228, PAGE_WIDTH - 70, PAGE_HEIGHT - 228, color=warm, line_width=1.8),
        _centered_text_command(PAGE_HEIGHT - 194, certificate_title, font="F1", size=27, color=accent_dark),
        _centered_text_command(PAGE_HEIGHT - 218, f"Fachbereich: {subject_label}" if subject_label else "Nova School Modullehrplan", font="F2", size=11.5, color=muted),
        _centered_text_command(PAGE_HEIGHT - 244, "Hiermit wird bestaetigt, dass", font="F2", size=13, color=muted),
        _centered_text_command(PAGE_HEIGHT - 308, student_name, font="F1", size=30, color=warm),
        _centered_text_command(PAGE_HEIGHT - 348, "den freigeschalteten Kurs erfolgreich abgeschlossen hat:", font="F2", size=14, color=ink),
        _centered_text_command(PAGE_HEIGHT - 396, course_title, font="F1", size=22, color=accent_dark),
        _centered_text_command(PAGE_HEIGHT - 446, f"Abschlussleistung: {score_text}", font="F2", size=14, color=ink),
        _centered_text_command(PAGE_HEIGHT - 474, f"Ausgestellt am {date_text}", font="F2", size=13, color=muted),
        _rect_command(58, 176, 214, 84, fill=(1.0, 1.0, 1.0), stroke=(0.83, 0.86, 0.84), line_width=0.8),
        _rect_command(PAGE_WIDTH - 198, 142, 140, 118, fill=(1.0, 1.0, 1.0), stroke=(0.83, 0.86, 0.84), line_width=0.8),
        _line_command(74, 126, 242, 126, color=accent, line_width=1.0),
        _line_command(PAGE_WIDTH - 250, 126, PAGE_WIDTH - 74, 126, color=accent, line_width=1.0),
        _text_command(78, 92, "Schulische Freigabe und Zertifizierung", font="F2", size=11, color=muted),
        _text_command(PAGE_WIDTH - 248, 92, "Digital signierter Nachweis", font="F2", size=11, color=muted),
        _text_command(78, 108, signatory_name, font="F2", size=13, color=ink),
        _text_command(78, 74, signatory_title, font="F2", size=10.5, color=muted),
        _text_command(78, 228, f"Pruefcode: {certificate_id}", font="F1", size=14, color=accent_dark),
        _text_command(78, 206, "Dieser Code dient zur Verifikation auf dem Nova School Server.", font="F2", size=10.4, color=muted),
        _text_command(78, 58, "Dieses Dokument wurde lokal auf dem Schulserver erstellt.", font="F2", size=9.5, color=muted),
    ]

    if logo:
        logo_width = 96.0
        logo_height = max(26.0, logo_width * (float(logo["height"]) / float(logo["width"])))
        stream_parts.append(_image_draw_command(58, PAGE_HEIGHT - 116, logo_width, logo_height, "ImLogo"))
        stream_parts.append(_text_command(168, PAGE_HEIGHT - 84, school_name, font="F1", size=24, color=(1.0, 1.0, 1.0)))
        stream_parts.append(_text_command(168, PAGE_HEIGHT - 106, "Nova School Server | Zertifikat des Modullehrplans", font="F2", size=11, color=(0.93, 0.97, 0.97)))
    else:
        stream_parts.extend(
            [
                _rect_command(58, PAGE_HEIGHT - 116, 78, 48, fill=(1.0, 1.0, 1.0), stroke=(0.88, 0.94, 0.93), line_width=1.0),
                _text_command(80, PAGE_HEIGHT - 97, _initials(school_name), font="F1", size=22, color=accent_dark),
                _text_command(154, PAGE_HEIGHT - 84, school_name, font="F1", size=24, color=(1.0, 1.0, 1.0)),
                _text_command(154, PAGE_HEIGHT - 106, "Nova School Server | Zertifikat des Modullehrplans", font="F2", size=11, color=(0.93, 0.97, 0.97)),
            ]
        )

    if verification_matrix:
        stream_parts.append(_image_draw_command(PAGE_WIDTH - 186, 150, 116, 116, "ImVerify"))
        stream_parts.append(_text_command(PAGE_WIDTH - 186, 270, "Pruefmatrix", font="F2", size=11, color=muted))

    verification_lines = _wrap_text(verification_url or f"code:{certificate_id}", max_chars=44)[:3]
    start_y = 184
    for index, line in enumerate(verification_lines):
        stream_parts.append(_text_command(78, start_y - (index * 15), line, font="F2", size=10.0, color=muted))

    stream = b"".join(stream_parts)

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    xobject_parts: list[bytes] = []
    next_object_number = 7
    if logo:
        xobject_parts.append(f"/ImLogo {next_object_number} 0 R ".encode("ascii"))
        next_object_number += 1
    if verification_matrix:
        xobject_parts.append(f"/ImVerify {next_object_number} 0 R ".encode("ascii"))
        next_object_number += 1
    xobject_section = b"/XObject << " + b"".join(xobject_parts) + b">> " if xobject_parts else b""

    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH:.0f} {PAGE_HEIGHT:.0f}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> {xobject_section}>> /Contents 6 0 R >>".encode("ascii")
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream")

    for image in [logo, verification_matrix]:
        if not image:
            continue
        objects.append(
            b"<< /Type /XObject /Subtype /Image /Width "
            + str(int(image["width"])).encode("ascii")
            + b" /Height "
            + str(int(image["height"])).encode("ascii")
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length "
            + str(len(image["stream"])).encode("ascii")
            + b" >>\nstream\n"
            + bytes(image["stream"])
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode("ascii")
        + b" /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode("ascii")
        + b"\n%%EOF"
    )
    return bytes(output)
