"""Image post-processing helpers for generated UMKM advertisements."""

from __future__ import annotations

import io
from typing import BinaryIO

from PIL import Image, ImageFilter


POSITION_FACTORS = {
    "Kiri Atas": (0.0, 0.0),
    "Kanan Atas": (1.0, 0.0),
    "Kiri Bawah": (0.0, 1.0),
    "Kanan Bawah": (1.0, 1.0),
    "Tengah Atas": (0.5, 0.0),
    "Tengah Bawah": (0.5, 1.0),
}


def _as_bytes(source: bytes | bytearray | BinaryIO) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if hasattr(source, "getvalue"):
        return bytes(source.getvalue())

    current_position = source.tell() if hasattr(source, "tell") else None
    data = source.read()
    if current_position is not None and hasattr(source, "seek"):
        source.seek(current_position)
    return data


def crop_to_aspect_ratio(image_bytes: bytes, ratio: tuple[int, int]) -> bytes:
    """Center-crop an image to an exact target ratio and return PNG bytes."""
    if not image_bytes:
        raise ValueError("Gambar utama tidak boleh kosong.")

    ratio_width, ratio_height = ratio
    if ratio_width <= 0 or ratio_height <= 0:
        raise ValueError("Rasio gambar harus bernilai positif.")

    with Image.open(io.BytesIO(image_bytes)) as source:
        image = source.convert("RGBA")

    target_ratio = ratio_width / ratio_height
    current_ratio = image.width / image.height

    if current_ratio > target_ratio:
        target_width = max(1, round(image.height * target_ratio))
        left = (image.width - target_width) // 2
        crop_box = (left, 0, left + target_width, image.height)
    else:
        target_height = max(1, round(image.width / target_ratio))
        top = (image.height - target_height) // 2
        crop_box = (0, top, image.width, top + target_height)

    cropped = image.crop(crop_box)
    output = io.BytesIO()
    cropped.save(output, format="PNG")
    return output.getvalue()


def apply_dynamic_branding(
    main_bytes: bytes,
    logo_source: bytes | bytearray | BinaryIO,
    position: str,
    *,
    width_ratio: float = 0.18,
    opacity: float = 0.9,
    shadow: bool = True,
) -> bytes:
    """Place a resized logo on a generated image with optional soft shadow."""
    if not main_bytes:
        raise ValueError("Gambar utama tidak boleh kosong.")
    if not logo_source:
        return main_bytes
    if position not in POSITION_FACTORS:
        raise ValueError(f"Posisi logo tidak didukung: {position}")
    if not 0.05 <= width_ratio <= 0.4:
        raise ValueError("Ukuran logo harus berada di antara 5% dan 40%.")
    if not 0.1 <= opacity <= 1.0:
        raise ValueError("Opacity logo harus berada di antara 10% dan 100%.")

    with Image.open(io.BytesIO(main_bytes)) as source:
        main_image = source.convert("RGBA")
    with Image.open(io.BytesIO(_as_bytes(logo_source))) as source:
        logo_image = source.convert("RGBA")

    target_width = max(1, round(main_image.width * width_ratio))
    target_height = max(1, round(target_width * logo_image.height / logo_image.width))
    max_height = max(1, round(main_image.height * 0.4))
    if target_height > max_height:
        target_height = max_height
        target_width = max(1, round(target_height * logo_image.width / logo_image.height))

    logo_image = logo_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    alpha = logo_image.getchannel("A").point(lambda value: round(value * opacity))
    logo_image.putalpha(alpha)

    padding = max(12, round(min(main_image.size) * 0.025))
    x_factor, y_factor = POSITION_FACTORS[position]
    available_x = main_image.width - target_width - (2 * padding)
    available_y = main_image.height - target_height - (2 * padding)
    x = padding + round(max(0, available_x) * x_factor)
    y = padding + round(max(0, available_y) * y_factor)

    result = main_image.copy()
    if shadow:
        shadow_layer = Image.new("RGBA", result.size, (0, 0, 0, 0))
        shadow_mask = Image.new("L", logo_image.size, 0)
        shadow_mask.paste(alpha)
        shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=max(2, target_width // 80)))
        shadow_color = Image.new("RGBA", logo_image.size, (0, 0, 0, 115))
        shadow_color.putalpha(shadow_mask)
        shadow_offset = max(3, target_width // 60)
        shadow_layer.alpha_composite(shadow_color, (x + shadow_offset, y + shadow_offset))
        result = Image.alpha_composite(result, shadow_layer)

    result.alpha_composite(logo_image, (x, y))
    output = io.BytesIO()
    result.save(output, format="PNG")
    return output.getvalue()
