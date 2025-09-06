from scipy.ndimage import generic_filter
def green_ratio(pixel):
    r, g, b = pixel[:3]
    total = r + g + b + 1e-5
    return g / total  # value between 0 and 1

def is_blurry_green(pixel, strong_thresh=0.6, weak_thresh=0.4):
    """
    Detect strong green (>0.6 ratio) and weak greens (~0.4-0.6) that usually appear in blur regions.
    """
    ratio = green_ratio(pixel)
    if ratio > strong_thresh:   # solid green
        return "green"
    elif weak_thresh < ratio <= strong_thresh:  # edge blur
        return "blurred"
    return "non-green"

def edge_mask(mask):
    """Find edges where green touches non-green."""
    # A pixel is on edge if in a 3x3 window both green and non-green exist
    def local_edge(values):
        return (np.any(values == 1) and np.any(values == 0))
    return generic_filter(mask.astype(int), local_edge, size=3)
