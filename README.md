# TVPAINT-EXPORT (work in progress, do not use)
# ==============

I wanted to be able to extract the image-data from a tvpaint-file (*.tvpp), for a more efficient
VFX-pipeline. To be able to automatically export the imagedata, without needing to run the tvpaint-application itself.
So I did a little digging with python and was able to extract the imagedata.

Update: version 1.0.0 (still) (24 june 2025)

I'm dumping my work in progress, is not finished yet



Update: version 1.0.0 (23 june 2025):

I decided to pickup this project in my free time to make it more usable. I refactered the proof-of-concept-code to be a bit more solid. It now also reads from file, instead of loading everything into
memory. It also can read images from random order. Also, the last piece of the imagepuzzle is solved,
so the images are now without errors.
I tested the code ith some tvpaint-files, version 9, 10 and till 11.5. TVPaint-version 8, and lower
is not supported yet. If someone can provide testprojects of late tvpaint-versions (12+), then let
me know, and I can test it, if needed.

A proof-of-concept-script to extract the imagedata from a tvpaint-file.



### Usage:
```sh
pip install opencv-python numpy jinja2
python -m tvpexport.tvpexport_demo tvpaintfile.tvpp
```
### About the imagedata
If I remember correctly:
The tvpaintformat(tvpaint-11.5) stores its imagedata as RLE-compressed blocks that are compared with the same block from previous frame, for changes. If the block is the same then nothing needs to be stored. Then everything can be zip-compressed, which is optional.

I hope this is useful. If any questions, let me know & I'll response if I have the time.


### Disclaimer
If something breaks or gets destroyed then it is not my fault or responsibility.

Have fun with it!

Kaspar
