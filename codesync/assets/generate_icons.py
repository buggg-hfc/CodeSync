"""Run once to generate the three tray icon PNGs."""
import struct, zlib, os

def _png_1x1(r, g, b):
    def chunk(tag, data):
        c = zlib.crc32(tag + data) & 0xffffffff
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", c)
    ihdr = struct.pack(">IIBBBBB", 16, 16, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes([r, g, b] * 16) for _ in range(16))
    idat = zlib.compress(raw)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")

icons = {
    "idle.png":     (39, 174, 96),    # green
    "syncing.png":  (41, 128, 185),   # blue
    "error.png":    (231, 76, 60),    # red
}

out = os.path.dirname(__file__)
for name, (r, g, b) in icons.items():
    with open(os.path.join(out, name), "wb") as f:
        f.write(_png_1x1(r, g, b))

print("Icons generated.")
