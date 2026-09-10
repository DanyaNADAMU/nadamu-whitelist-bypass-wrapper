"""
QR code generation service for WhitelistBypass Core.
Provides terminal ANSI UTF-8 output, SVG, and Base64-encoded PNG images.
"""

import base64
import io
import shutil
import subprocess
from typing import Optional


class QrService:
    @staticmethod
    def is_qrencode_available() -> bool:
        return shutil.which("qrencode") is not None

    @classmethod
    def render_ansi(cls, text: str) -> Optional[str]:
        """
        Render QR code as ANSI UTF-8 string suitable for direct terminal display.
        Uses qrencode -t ANSIUTF8 -m 2 if available, or python qrcode fallback.
        """
        if not text:
            return None

        # 1. Try qrencode utility
        if cls.is_qrencode_available():
            try:
                proc = subprocess.run(
                    ["qrencode", "-t", "ANSIUTF8", "-m", "2", text],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    return proc.stdout
            except Exception:
                pass

        # 2. Try python qrcode library
        try:
            import qrcode  # type: ignore

            qr = qrcode.QRCode(border=2)
            qr.add_data(text)
            qr.make(fit=True)
            output = io.StringIO()
            qr.print_ascii(out=output, invert=True)
            return output.getvalue()
        except Exception:
            pass

        return None

    @classmethod
    def render_png_base64(cls, text: str) -> Optional[str]:
        """
        Generate PNG image of QR code and return it as base64-encoded data string.
        """
        if not text:
            return None

        # 1. Try python qrcode with PIL
        try:
            import qrcode  # type: ignore

            qr = qrcode.QRCode(border=2)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except Exception:
            pass

        # 2. Try qrencode command
        if cls.is_qrencode_available():
            try:
                proc = subprocess.run(
                    ["qrencode", "-t", "PNG", "-m", "2", "-o", "-", text],
                    capture_output=True,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout:
                    return base64.b64encode(proc.stdout).decode("ascii")
            except Exception:
                pass

        return None

    @classmethod
    def render_svg(cls, text: str) -> Optional[str]:
        """
        Generate SVG vector string of QR code.
        """
        if not text:
            return None

        if cls.is_qrencode_available():
            try:
                proc = subprocess.run(
                    ["qrencode", "-t", "SVG", "-m", "2", "-o", "-", text],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout:
                    return proc.stdout
            except Exception:
                pass

        try:
            import qrcode  # type: ignore
            import qrcode.image.svg  # type: ignore

            factory = qrcode.image.svg.SvgPathImage
            img = qrcode.make(text, image_factory=factory, border=2)
            buf = io.BytesIO()
            img.save(buf)
            return buf.getvalue().decode("utf-8")
        except Exception:
            pass

        return None
