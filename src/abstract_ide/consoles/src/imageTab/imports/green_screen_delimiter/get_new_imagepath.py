import os
# ---------- path helper ----------
def get_new_image_path(input_image, basename, func=None, dir_name=None, **kwargs):
    """
    Build an output path under <input dir>/<dir_name or 'new_pics'>/<basename>,
    optionally run func(input_path, output_path, **kwargs).
    """
    dir_name = dir_name or 'new_pics'
    dirname = os.path.dirname(input_image)
    out_dir = os.path.join(dirname, dir_name)
    os.makedirs(out_dir, exist_ok=True)
    output_image = os.path.join(out_dir, basename)
    if func:
        func(input_image, output_image, **kwargs)
    return output_image
