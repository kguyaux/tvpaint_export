TVPAINT-EXPORT
==============

Export images from a tvpaint-project(*.tvpp). Supported tvpaint-versions are 9,10, & 11. (12+ is untested)

### Changelog:
- version 1.0.0  (27 june 2025)  
The previous version was just a proof of concept and not very usable.
I revised the code to make it more usable. It still needs some refactoring and documentation. I will do that when I have time.  
I tested the code with some tvpaint-files, from tvpaint-versions 9, 10 & 11. There might be some specific cases of datastorage that need to be resolved.
If you encounter errors, then let me know or file an issue.

### TODO:
- handle multiple clips and scenes. I don't have example-tvp-projects that contain multiple scenes/clips. Expect errors when your project has those. I need an example to fix the code for this, so If someone has an example-tvpp with multiple clips/scenes and can send it to me then that would be nice :-)

### Usage:
```sh
$ pip install opencv-python numpy
$ python -m tvpexport -h

usage: __main__.py [-h] [-d] [-l LAYER] [-f FRAME] [-s] [-i] [-o OUTPUT_DIR] tvpp

Export images from a tvpaint-project.

positional arguments:
  tvpp                  Path of TVPaint project file (.tvpp)

options:
  -h, --help            show this help message and exit
  -d, --debug           Show debug info.
  -l LAYER, --layer LAYER
                        index of the layer to inspect (from top to bottom = [0:])
  -f FRAME, --frame FRAME
                        Which frame to choose, omitting this will process all frames of the layer.
  -s, --show            Display image.
  -i, --interactive     Slideshow-mode: press key for next frame(ESC to quit)
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output-dir of where to save images(overwrites!).

#example:
python -m my_tvpaint-project_v004.tvpp -d -l 0 -s -o output_dir
# will show debugmessages while auto-showing all images of layer 0 (index = top to bottom), and save the images as png to directory 'output_dir'
```

### Disclaimer
If something breaks or gets destroyed then it is not my fault or responsibility.

Have fun with it!

Kaspar
