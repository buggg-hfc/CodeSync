"""Generate tray icons: sync arrows body + status dot on bottom-right."""
from PIL import Image, ImageDraw
import os

SIZE = 16
OUT_DIR = os.path.dirname(__file__)

# Status colors (R, G, B)
STATUS_COLORS = {
    "idle":    (39, 174, 96),    # green
    "syncing": (41, 128, 185),   # blue
    "error":   (231, 76, 60),    # red
}

def draw_sync_arrows(draw, color=(255,255,255)):
    """Draw simple double arrow cycle (white lines on 16x16)"""
    # Left arc arrow (top half counterclockwise)
    draw.arc([2, 1, 13, 12], start=180, end=360, fill=color, width=1)
    # Top-left arrow head
    draw.polygon([(3,3), (1,5), (5,5)], fill=color)
    # Right arc arrow (bottom half clockwise)
    draw.arc([-3, 4, 8, 15], start=0, end=180, fill=color, width=1)
    # Bottom-right arrow head
    draw.polygon([(12,11), (10,13), (14,13)], fill=color)

def create_icon(status_color):
    """Create complete icon: white sync arrows + status dot bottom-right"""
    # Transparent background
    img = Image.new("RGBA", (SIZE, SIZE), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # 1. Body: white sync arrows
    draw_sync_arrows(draw, (255,255,255))

    # 2. Bottom-right status dot (radius 3)
    x0, y0 = SIZE-5, SIZE-5
    draw.ellipse([x0, y0, x0+5, y0+5], fill=status_color, outline=None)

    return img

# Generate three files
for state, rgb in STATUS_COLORS.items():
    icon = create_icon(rgb)
    filename = f"{state}.png"
    icon.save(os.path.join(OUT_DIR, filename))

print("Generated idle.png, syncing.png, error.png")
