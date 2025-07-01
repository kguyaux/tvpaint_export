import argparse
import sys
import logging
import os
import numpy as np
import cv2
import time
from pprint import pprint
from .parser import TvpProject
from .data_handlers import Clip

import cProfile
import pstats


logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)


def show_window(tvpp, bg_color, img, timeout=0):

    # TVPaint 9 stores pixeldata as ABGR
    if tvpp.tvpaint_version[0] == 9:
        alpha = img[:, :, 0].astype(float) / 255
        fg = alpha[:, :, np.newaxis] * img[:, :, 1:].astype(float) / 255
        fg = fg[:, :, ::-1] # swap rgb for older versions.
    else:  # 10 and upper store pixeldata as RGBA
        alpha = img[:, :, 3].astype(float) / 255
        fg = alpha[:, :, np.newaxis] * img[:, :, :3].astype(float) / 255

    background = (
        np.zeros(shape=(img.shape[0], img.shape[1], 3), dtype=float) + [c / 255 for c in bg_color[:3]]
    )
    bg = (1 - alpha[:, :, np.newaxis]) * background
    res = cv2.add(fg, bg)
    res = (res * 255).astype(np.uint8)

    window_name = "Image Fit to Display"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    target_width = 1024
    target_height = 1024
    cv2.resizeWindow(window_name, target_width, target_height)
    cv2.imshow(window_name, res)
    x = cv2.waitKey(timeout)
    if x==27:    # Esc key to stop
        cv2.destroyAllWindows()
        sys.exit(0)


def save_img(tvpp, layer, img, index, output_dir):
    if not os.path.exists(output_dir):
        raise FileNotFoundError(f"'{output_dir}' does not exist")

    file_name = f"{layer.name.replace('_', '-')}_{index:04d}.png"
    file_path = os.path.join(output_dir, file_name)
    if tvpp.tvpaint_version[0] == 9:
        img = img[:, :, ::-1]
    logger.info(f"Saving to {file_path}.")
    cv2.imwrite(file_path, img)


def main():
    parser = argparse.ArgumentParser(
        description="Export images from a tvpaint-project."
    )
    parser.add_argument(
        "tvpp",
        type=str,
        help="Path of TVPaint project file (.tvpp)"
    )
    parser.add_argument('-d',
        "--debug",
        action="store_true",
        help="Show debug info."
    )
    parser.add_argument('-l',
        "--layer",
        type=int,
        help="index of the layer to inspect (from top to bottom = [0:])"
    )

    parser.add_argument('-f',
        "--frame",
        type=int,
        help="Which frame to choose, omitting this will process all frames of the layer."
    )
    parser.add_argument('-s',
        "--show",
        action="store_true",
        help="Display image."
    )

    parser.add_argument('-i',
        "--interactive",
        action="store_true",
        help="Slideshow-mode: press key for next frame(ESC to quit)"
    )
    parser.add_argument('-o',
        "--output_dir",
        type=str,
        help="Output-dir of where to save images(overwrites!)."
    )

    args = parser.parse_args()
    if args.debug:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)


    tvptree = TvpProject(args.tvpp)
    clip = Clip(tvptree)
    pprint(clip.metadata)

    if args.layer is not None:
        layer = clip.layers[args.layer]
        pprint(layer.settings)
        if args.frame is not None:
            start_time = time.time()
            image = layer.frame(args.frame)
            logger.info(
                f"Frame {args.frame}, processing took: {time.time() - start_time:.6f} seconds"
            )

            if args.show:
                show_window(tvptree, clip.bgp1, image)
            if args.output_dir:
                save_img(tvptree, layer, img, args.frame, args.output_dir)
        else:
            end_frame = max([l.settings['end_frame'] for l in clip.layers])
            for i in range(end_frame + 1):
                start_time = time.time()
                img = layer.frame(i)
                logger.info(
                    f"Frame {i}, processing took: {time.time() - start_time:.6f} seconds"
                )
                if args.show:
                    if args.interactive:
                        show_window(tvptree, clip.bgp1, img)
                    else:
                        show_window(tvptree, clip.bgp1, img, timeout=100)
                if args.output_dir:
                    save_img(tvptree, layer, img, i, args.output_dir)


if __name__ == "__main__":
    profile_output_file = "my_profile_data.prof"
    cProfile.run('main()', profile_output_file)

    # 2. Load the stats from the file
    stats = pstats.Stats(profile_output_file)

    # 3. Sort by 'ncalls'
    stats.sort_stats('ncalls') # Or 'ncalls' as a string

    # 4. Reverse the order (lowest ncalls first)
    # Note: pstats.Stats.reverse_stats() reverses the *current* sort order.
    stats.reverse_order()

    # 5. Print the stats
    stats.print_stats()
