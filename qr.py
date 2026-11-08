"""Generates a QR code that opens Google Maps directions to an address when scanned."""
import io
import urllib.parse

import qrcode


def directions_url(address: str) -> str:
    q = urllib.parse.quote(address.strip())
    return f"https://www.google.com/maps/dir/?api=1&destination={q}"


def directions_qr_png_bytes(address: str) -> bytes:
    url = directions_url(address)
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    import sys

    addr = " ".join(sys.argv[1:]) or "270 Claremont Ave, Montclair, NJ"
    out = "address_qr.png"
    with open(out, "wb") as f:
        f.write(directions_qr_png_bytes(addr))
    print(f"Saved {out} -> {directions_url(addr)}")
