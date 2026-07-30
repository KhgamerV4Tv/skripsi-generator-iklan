import io
import unittest

from PIL import Image

from utils.branding import apply_dynamic_branding, crop_to_aspect_ratio


def png_bytes(size, color):
    output = io.BytesIO()
    Image.new("RGBA", size, color).save(output, format="PNG")
    return output.getvalue()


class BrandingTests(unittest.TestCase):
    def test_crop_to_vertical_story_ratio(self):
        result = crop_to_aspect_ratio(png_bytes((1024, 1536), "white"), (9, 16))
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.size, (864, 1536))

    def test_crop_to_landscape_ratio(self):
        result = crop_to_aspect_ratio(png_bytes((1536, 1024), "white"), (16, 9))
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.size, (1536, 864))

    def test_branding_preserves_canvas_and_returns_png(self):
        main = png_bytes((800, 600), "white")
        logo = png_bytes((200, 100), (255, 0, 0, 220))
        result = apply_dynamic_branding(
            main,
            logo,
            "Kanan Bawah",
            width_ratio=0.2,
            opacity=0.8,
            shadow=True,
        )
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.size, (800, 600))
            self.assertEqual(image.format, "PNG")

    def test_unknown_position_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_dynamic_branding(
                png_bytes((100, 100), "white"),
                png_bytes((20, 20), "red"),
                "Posisi Tidak Valid",
            )


if __name__ == "__main__":
    unittest.main()
