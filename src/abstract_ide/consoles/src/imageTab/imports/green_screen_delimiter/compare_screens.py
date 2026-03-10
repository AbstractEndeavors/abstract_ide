from PIL import Image
import os

from .detect_allgreen import  *
from .detect_green_screen_blur import  *
from .get_new_imagepath import  *


def compareGreenScreens(input_image, *, dir_name="new_pics", **kwargs):
    """
    Generates a side-by-side comparison of:
      - left: all detected green pixels
      - right: only blurred/edge green pixels
    """
    # First run your two detectors and save temp outputs
    out_all = get_new_image_path(
        input_image=input_image,
        basename="all_green_tmp.png",
        func=detect_all_green,
        dir_name=dir_name,
        **kwargs
    )
    out_blur = get_new_image_path(
        input_image=input_image,
        basename="blur_tmp.png",
        func=detect_greenscreen_blur,
        dir_name=dir_name,
        **kwargs
    )

    # Load both results
    img_all = Image.open(out_all).convert("RGBA")
    img_blur = Image.open(out_blur).convert("RGBA")

    # Match heights (resize blur if needed)
    if img_all.size[1] != img_blur.size[1]:
        img_blur = img_blur.resize((img_blur.width, img_all.height))

    # Combine side by side
    w, h = img_all.size[0] + img_blur.size[0], img_all.size[1]
    combined = Image.new("RGBA", (w, h))
    combined.paste(img_all, (0, 0))
    combined.paste(img_blur, (img_all.size[0], 0))

    # Save combined comparison
    dirname = os.path.dirname(out_all)
    out_combined = os.path.join(dirname, "greenscreen_comparison.png")
    combined.save(out_combined, "PNG")

    return out_combined
