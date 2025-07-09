TVPAINT-EXPORT (v1.1.2)
==============

With this tool you can save(export) the images from a tvpaintfile(*.tvpp). With this it is easier to automate the
export of layers&images for compositing. And probably other uses like dumping the salvageable contents of a
corrupt tvpaint-file. There are some features I like to add, like the blending/compositing of
layers. I also have plans to create a Blender-plugin, to directly load the layers into the compositor(without the need of intermediate exports)  

This is a 'reverse-engineering'-project so a lot of tvpaint features, like sound, scribbles and other
stuff are not resolved(yet). But feel free to fork/clone and figure them out yourself :-)
Supported tvpaint-versions are 9,10, & 11. (12+ is untested)

### Changelog:
- version 1.1.2  (9 july 2025)
Cleanup, error-handling and a test-arg.

- version 1.1.1  (6 july 2025)
Some optimizations. faster RLE- & Unzip-decompression. Prevented unnecessary RLE-decompress

- version 1.1.0  (4 july 2025)
Improved the tile-resolving. It should be free of bugs now (No more distorted tiles)
Also some cleanup, some more data-handling. You also should be able to read the blendmode of a layer (Layer(...).settings['blendmode'])
I don't have a lot of tvpp-samples so I only can affirm that blendmode 9 means 'multiply', amd 0 means 'color'. Also slightly faster RLE-decompressing.

- version 1.0.0  (27 june 2025)
The previous version was just a proof of concept and not very usable.
I revised the code to make it more usable. It still needs some refactoring and documentation. I will do that when I have time.
I tested the code with some tvpaint-files, from tvpaint-versions 9, 10 & 11. There might be some specific cases of datastorage that need to be resolved.
If you encounter errors, then let me know or file an issue.

### Dependencies(python)
- opencv-python
- numpy

### TODO:
- To be able to process layer- and image-arguments as a list.
- compositing; being able to merge(blend) layers.
- handle multiple clips and scenes. I don't have example-tvp-projects that contain multiple scenes/clips. Expect errors when your project has those. I need an example to fix the code for this, so If someone has an example-tvpp with multiple clips/scenes and can send it to me then that would be nice :-)

### Usage:
```sh
$ pip install opencv-python numpy
$ python -m tvpexport -h

usage: __main__.py [-h] [-d] [-a] [-l LAYER] [-f FRAME] [-s] [-i] [-o OUTPUT_DIR] [-p] tvpaint-file()

Export images from a tvpaint-project.

positional arguments:
  tvpp                  Path of TVPaint project file (.tvpp)

options:
  -h, --help            show this help message and exit
  -d, --debug           Show debug info.
  -a, --all_layers      Process all layers
  -l LAYER, --layer LAYER
                        index of the layer to process (from top to bottom = [0:])
  -f FRAME, --frame FRAME
                        Which frame to choose, omitting this will process all frames of the layer.
  -s, --show            Display image.
  -i, --interactive     Slideshow-mode: press key for next frame(ESC to quit)
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output-dir of where to save images(overwrites!).
  -p, --print_info      Print info of everything (project, clip, scene, layer)
  -t, --test            Test all processing, use this without the --show option for quicker testing.


# EXAMPLE1: will show debugmessages while auto-showing all images of layer 0 (index = top to bottom), and save the images as png to directory 'output_dir'
python -m my_tvpaintproject_v004.tvpp -d -l 0 -s -o output_dir

# EXAMPLE2: will only print info and debug-messages, about project, scene0 , clip0, layer2
python -m tvpexport my_tvpaintproject.tvpp -l 2 -p -d

#EXAMPLE3: will show frame no. '2' of every layer, and save it in directory 'output', and wait for a
# keypress to process next.
python -m tvpexport my_tvpaintproject.tvpp -d -a -f 2 -i -s -o output

#EXAMPLE4: Just dump all images of all layers in directory 'output'
python -m tvpexport my_tvpaintproject.tvpp -a -o output
```

### Disclaimer
If something breaks or gets destroyed then it is not my fault or responsibility.

Have fun with it!

Kaspar

