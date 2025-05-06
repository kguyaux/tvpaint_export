# TVPAINT-EXPORT

A proof-of-concept-script to extract the imagedata from a tvpaint-file.

I wanted to be able to extract the image-data from a tvpaint-file (*.tvpp), for a more efficient VFX-pipeline. To be able to automatically export the imagedata, without needing the tvpaint-application itself.
So I did a little digging with python and was able to extract the imagedata.  
The tvpaint-version was 11.5, if I remember correctly.  
I don't work with tvpaint atm so I have no need(or time) to develop it further into an app.

Maybe someone can use this?
For example, to make a nice plugin to load the imagelayers directly into blender or nuke?

### Usage:  
```sh
pip install opencv-python numpy jinja2
python tvpexport_demo.py tvpaintfile.tvpp
```
### About the imagedata
If I remember correctly:  
The tvpaintformat(tvpaint-11.5) stores its imagedata as RLE-compressed blocks that are compared with the same block from previous frame, for changes. If the block is the same then nothing needs to be stored. Then everything can be zip-compressed, which is optional.

I hope this is useful. If any questions, let me know & I'll response if I have the time.

### Disclaimer
This is a proof-of-concept-script, and if something breaks or gets destroyed then it is not my fault or responsibility.
All is very much in a research-state, that's why it looks a bit cryptic.
Maybe a bug here and there.. oh well

Have fun with it!

Kaspar