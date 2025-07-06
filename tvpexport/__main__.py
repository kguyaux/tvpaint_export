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

    file_name = f"{layer.index:03d}_{index:04d}.png"
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

    parser.add_argument('-a',
        "--all_layers",
        action="store_true",
        help="Process all layers"
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
    parser.add_argument('-p',
        "--print_info",
        action="store_true",
        help="Print info of everything (project, clip, scene, layer)"
    )

    args = parser.parse_args()
    if args.debug:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

    tvptree = TvpProject(args.tvpp)
    scene = tvptree.get_scene_tree(scene_index=0)
    clip = Clip(tvptree, scene_index=0, clip_index=0)

    if args.print_info:
        pprint(tvptree.metadata)
        pprint(tvptree.read_scene_metadata(scene))
        pprint(clip.metadata)

    layers = []
    if args.all_layers:
        layers = clip.layers

    if args.layer is not None:
        layers = [clip.layers[args.layer]]

    for layer in layers:
        if args.print_info:
            pprint(layer.settings)

        # for faster testing the imageprocessing, you can comment this out.
        if not args.output_dir and not args.show:
            sys.exit(0)

        if args.frame is not None:
            start_time = time.time()
            image = layer.frame(args.frame)
            logger.info(
                f"Layer {layer.index} (\"{layer.name}\"), Frame {args.frame}, processing took: {time.time() - start_time:.6f} seconds"
            )

            if args.show:
                if args.interactive:
                    show_window(tvptree, clip.bgp1, image)
                else:
                    show_window(tvptree, clip.bgp1, image, timeout=10)

            if args.output_dir:
                save_img(tvptree, layer, image, args.frame, args.output_dir)
        else:
            end_frame = max([l.settings['end_frame'] for l in clip.layers])
            for i in range(end_frame + 1):
                start_time = time.time()
                image = layer.frame(i)
                logger.info(
                    f"Layer {layer.index} (\"{layer.name}\") Frame {i}, processing took: {time.time() - start_time:.6f} seconds"
                )
                if args.show:
                    if args.interactive:
                        show_window(tvptree, clip.bgp1, image)
                    else:
                        show_window(tvptree, clip.bgp1, image, timeout=10)
                if args.output_dir:
                    save_img(tvptree, layer, image, i, args.output_dir)


if __name__ == "__main__":
    main()
