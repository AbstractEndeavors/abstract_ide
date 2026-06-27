from PIL import Image
import numpy as np
import os
# ---------- green classification ----------
def _green_ratio(px):
    r = px[..., 0].astype(np.float32)
    g = px[..., 1].astype(np.float32)
    b = px[..., 2].astype(np.float32)
    total = r + g + b + 1e-5
    return g / total

def greenish_mask(px, strong_thresh=0.60, weak_thresh=0.40):
    ratio = _green_ratio(px)
    strong = ratio > strong_thresh
    weak = (ratio > weak_thresh) & (~strong)
    return strong | weak

# ---------- detectors ----------
def detect_all_green(input_path, output_path, strong_thresh=0.60, weak_thresh=0.40):
    """
    Keep ALL green-ish pixels (strong + weak) in original colors; everything else transparent.
    """
    img = Image.open(input_path).convert("RGBA")
    px = np.array(img, dtype=np.uint8)

    greenish = greenish_mask(px, strong_thresh, weak_thresh)

    out = np.zeros_like(px, dtype=np.uint8)
    out[greenish] = px[greenish]
    out[..., 3] = np.where(greenish, 255, 0).astype(np.uint8)

    Image.fromarray(out, mode="RGBA").save(output_path, "PNG")
