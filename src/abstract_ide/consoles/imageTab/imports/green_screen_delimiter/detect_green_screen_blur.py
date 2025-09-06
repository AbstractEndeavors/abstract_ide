from PIL import Image
import numpy as np
from scipy.ndimage import generic_filter


def green_ratio(pixel):
    r, g, b = pixel[:3]
    total = r + g + b + 1e-5
    return g / total

def classify_pixel(pixel, strong_thresh=0.6, weak_thresh=0.4):
    ratio = green_ratio(pixel)
    if ratio > strong_thresh:
        return 2  # strong green
    elif weak_thresh < ratio <= strong_thresh:
        return 1  # blurred/edge green
    return 0  # non-green

def detect_greenscreen_blur(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    pixels = np.array(img)

    # classify all pixels
    mask = np.apply_along_axis(classify_pixel, 2, pixels)
    
    # find edges between green (1/2) and non-green (0)
    def local_edge(values):
        return (np.any(values > 0) and np.any(values == 0))
    edge = generic_filter((mask > 0).astype(int), local_edge, size=3)

    # Build visualization: red for blurred edge, keep rest transparent
    output = np.zeros_like(pixels)
    
    #output[edge == 1] = [255, 0, 0, 255]
    output[edge == 1] = pixels[edge == 1]  # keep original color
    result = Image.fromarray(output, mode="RGBA")
    result.save(output_path, "PNG")


def detect_greenscreen_blur_thresh(input_path, output_path, strong_thresh=0.60, weak_thresh=0.40):
    img = Image.open(input_path).convert("RGBA")
    pixels = np.array(img)
    
    # Classify all pixels
    mask = np.apply_along_axis(lambda p: classify_pixel(p, strong_thresh, weak_thresh), 2, pixels)
    
    # Find edges between green (1/2) and non-green (0)
    def local_edge(values):
        return (np.any(values > 0) and np.any(values == 0))
    edge = generic_filter((mask > 0).astype(int), local_edge, size=3)
    
    # Build visualization:
    # - Strong green (mask == 2): Green color
    # - Weak green (mask == 1): Red color (indicating blur/edge)
    # - Edge regions (edge == 1): Red if weak green, green if strong green
    # - Non-green (mask == 0): Transparent
    output = np.zeros_like(pixels)
    
    # Set strong green pixels (mask == 2)
    output[mask == 2] = [0, 255, 0, 255]  # Green for strong green
    
    # Set weak green pixels (mask == 1)
    output[mask == 1] = [255, 0, 0, 255]  # Red for weak green
    
    # Override edge pixels to highlight them (optional, can skip if you want edges to follow mask colors)
    # output[edge == 1] = [255, 0, 0, 255]  # Red for edges (uncomment to highlight all edges in red)
    
    # Alternative: Keep original colors for non-edge regions to show context
    # output[mask == 0] = pixels[mask == 0]  # Uncomment to keep original colors for non-green areas
    
    result = Image.fromarray(output, mode="RGBA")
    result.save(output_path, "PNG")
