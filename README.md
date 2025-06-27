# TVPAINT-EXPORT
# ==============

I wanted to be able to extract the image-data from a tvpaint-file (*.tvpp), for a more efficient
VFX-pipeline. To be able to automatically export the imagedata, without needing to run the tvpaint-application itself.
So I did a little digging with python and was able to extract the imagedata.

Update 24 june 2025.
First verson was just a proof of concept and not very usable.
I revised the code to make it more usable. It still needs some refactoring and documentation. I will do that when I have time.

I tested the code with some tvpaint-files, from tvpaint-versions 9, 10 & 11. There might be some cases of data storage that need to be resolved.
If you encounter, then let me know or file an issue.




### Usage:
```sh
$ pip install opencv-python numpy
$ python -m tvpexport -h
usage: __main__.py [-h] [-d] [-l LAYER] [-f FRAME] [-s] [-i] [-o OUTPUT_DIR] tvpp

Demo for exporting and inspecting TVPaint project files. Only first clip is supported(yet)

positional arguments:
  tvpp                  Path to the TVPaint project file (.tvpp)

options:
  -h, --help            show this help message and exit
  -d, --debug           Show debug info
  -l LAYER, --layer LAYER
                        index of the layer to inscpect (from top to bottom = [0:])
  -f FRAME, --frame FRAME
                        Which frame to choose, omitting this will process all
  -s, --show            Show image
  -i, --interactive     Slideshow-mode: press key for next frame
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output-dir of where to save images(overwrites)

#example:
python -m my_tvpaint-project_v004.tvpp -d -l 0 -s -o output_dir
# will show debugmessages while auto-showing all images of layer 0 (index = top to bottom), and save the images as png tp directory 'output_dir'
```

### Disclaimer
If something breaks or gets destroyed then it is not my fault or responsibility.

Have fun with it!

Kaspar
