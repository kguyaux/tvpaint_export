""" A demo for the TvPTree an LayerData-classes

Issued under the "do what you like with it - I take no respnsibility" licence                                                                                                                                                     
"""

import sys
import os
from jinja2 import Template
import subprocess
from tvpexport.parser import TvpTree
from tvpexport.layerdata import LayerData


def printformat_nested_dict(dict_obj, indent=0):
    """Pretty Print nested dictionary with given indent level"""

    text = []
    for key, value in dict_obj.items():
        # If value is dict type, then print nested dict
        if isinstance(value, dict):
            text.append("<b>{}{}{}</b><br>".format("&emsp;" * indent, key, ":"))
            text.append(printformat_nested_dict(value, indent + 1))
            # text.append('{}{}<br>'.format('&emsp;' * indent, '}'))
        else:
            text.append(
                "{}{}{}{}<br>".format("&emsp;" * indent, key, "&nbsp;:&nbsp;", value)
            )
    return "\n".join(text)


def create_thumbnails(layers):
    html = []
    html.append("<b>Contents:</b><br>")
    html.append(
        '<table style="background-color:#DFDFDF;" cellpadding="0px" cellspacing="4" border="0">'
    )
    html.append("<tr>")
    html.append('<td width="150px" align="center"><b>layername:</b></td>')
    html.append("</tr>")

    for layer_index, info in layers.items():
        html.append("<tr>")
        html.append('<td width="150px" align="right">')
        layername = info["name"]
        html.append(layername)
        html.append("</td>")
        html.append('<td align="left">')
        html.append('<th nowrap="nowrap" align="left">')
        for img_index in info["images"]:
            img_file = "layer{:03d}_{:03d}.jpg".format(layer_index, img_index)
            img_path = os.path.join("/tmp/tvpp_export", img_file)
            html.append(
                '<a href="file://{0}"> <img src="{0}" width=40" height="30"></a>'.format(
                    img_path
                )
            )
        html.append("</th>")
        html.append("</td>")
        html.append("</tr>")
    html.append("</table>")
    return "\n".join(html)


def create_template(info, layers):
    func_dict = {
        "print_nested_dict": printformat_nested_dict,
        "create_thumbnails": create_thumbnails,
    }

    tm = Template(
        """
        <p style="font-family:arial;color:darkbrown;font-size:12px;">
            {{ create_thumbnails(layers) }}
        <br>
            {{ print_nested_dict(info) }}
        </p>
        """
    )
    tm.globals.update(func_dict)
    return tm.render(info=info, layers=layers)


if __name__ == "__main__":
    filepath = sys.argv[1]
    tvptree = TvpTree(filepath)
    tvptree.printnode(tvptree.root)

    write_dir = "/tmp/tvpp_export"
    if not os.path.exists(write_dir):
        os.makedirs(write_dir)

    print(len(tvptree.root.children))

    info = {
        "project_info": tvptree.root.children[0].parse_info(),
        # 'sound_info': tvptree.root.children[2].parse_info(),
        # 'lib_info': tvptree.root.children[3].parse_info(),
        # 'object_info': tvptree.root.children[5].children[0].parse_info(),
        # 'root_info': tvptree.root.children[5].children[1].children[0].children[0].parse_info()
    }

    WIDTH = int(info["project_info"]["Width"])
    HEIGHT = int(info["project_info"]["Height"])
    tdata = tvptree.root.children[6:]
    formdata = tdata[0].children[1].children[1]

    layerdata = LayerData(write_dir, WIDTH, HEIGHT)
    layers = layerdata.process_layers(formdata, write_dir)

    html = create_template(info, layers)
    htmlfilepath = "/tmp/{}.html".format(os.path.basename(filepath))
    with open(htmlfilepath, "w") as f:
        f.write(html)
    p = subprocess.Popen(["firefox", htmlfilepath])
