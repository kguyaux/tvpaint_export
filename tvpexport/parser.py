""" Parse tvpaintfile-data into a datastructure.

From this structure you can access data, to analyze and process.

Issued under the "do what you like with it - I take no responsibility" licence.
"""

import sys
import re
import struct
import codecs
import logging
from . import decoders

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Node(object):
    """ A tree-item for the tvpaint-project-tree-structure.
    """

    def __init__(self):
        self.type = ""
        # self.header = None
        self.data_offset = 0  # Position(index) of datablock in file
        # read size of node-data
        self.size = 0
        self.data = None
        self.data_seek = 0
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def add_data(self, data):
        self.data = data


class TvpProject(object):
    """ Class for a tvpaint-data-tree.

    A tvpaint-tree, is a tree of data-blocks.
    (for example; this is from a tvpaint-11-project):

    project
    ---- utf16-projectinfo
    ---- thumbnail
    -------- utf16-thumbnailinfo
    -------- thumbnail-data
    ---- utf8-soundinfo
    ---- utf8-labelinfo
    ---- zeros
    ---- unknown-object
    -------- utf16-info
    -------- e5 c9 20 a8
    ------------ e5 c9 df 8e
    ---------------- utf8-object
    -------- e5 c9 60 7c
    ---- scene
    -------- utf16-scene-info
    -------- clip
    ------------ utf16-clip-info
    ------------ clip-data

    This class provides a 'root'-object that contains this tree, so we can
    access its data.
    """

    def __init__(self, file_path):
        self.headers = {
            "project": {
                "header": (0x33, 0x84, 0x78, 0x0E),
                "is_data": False
            },
            "utf16-projectinfo": {
                "header": (0x33, 0x85, 0x55, 0x3A),
                "is_data": True
            },
            "thumbnail": {
                "header": (0x33, 0x8C, 0x4E, 0xE4),
                "is_data": False
            },
            "utf16-thumbnailinfo": {
                "header": (0x33, 0x8A, 0x96, 0x08),
                "is_data": True
            },
            "thumbnail-data": {
                "header": (0x33, 0x8B, 0x71, 0x54),
                "is_data": True
            },
            "utf8-soundinfo": {
                "header": (0x04, 0x56, 0x69, 0x28),
                "is_data": True
            },
            "utf8-labelinfo": {
                "header": (0x33, 0x8E, 0x0A, 0xEA),
                "is_data": True
            },
            "zeros": {
                "header": (0x33, 0xFB, 0x9B, 0xE6),
                "is_data": True
            },
            "unknown1": {
                "header": (0xE5, 0xC8, 0xE0, 0x7A),
                "is_data": False
            },
            "utf8-object": {
                "header": (0xE5, 0xCA, 0xDE, 0xAC),
                "is_data": True
            },
            "utf16-info": {
                "header": (0xE5, 0xCB, 0x5E, 0x68),
                "is_data": True
            },
            "scene": {
                "header": (0x33, 0x86, 0x31, 0xB2),
                "is_data": False
            },
            "utf16-scene-info": {
                "header": (0x33, 0x88, 0xDA, 0x98),
                "is_data": True
            },
            "clip": {
                "header": (0x33, 0x89, 0xB8, 0x46),
                "is_data": False
            },
            "utf16-clip-info": {
                "header": (0x33, 0x87, 0xE3, 0x4A),
                "is_data": True
            },
            "clip-data": {
                "header": (0x33, 0x87, 0x11, 0x54),
                "is_data": True
            },
            "unknown2": {
                "header": (0xE5, 0xC9, 0x20, 0xA8),
                "is_data": False
            },
            "unknown3": {
                "header": (0xE5, 0xC9, 0x60, 0x7C),
                "is_data": False
            },
            "unknown4": {
                "header": (0xE5, 0xC9, 0xDF, 0x8E),
                "is_data": False
            },
            "unknown5": {
                "header": (0x33, 0xfd, 0x54, 0x54),
                "is_data": True
            }
        }
        self.file_path = file_path
        self.root = Node()
        with open(self.file_path, "rb") as file_obj:
            self.process(file_obj, self.root)

        self.metadata = self.read_project_metadata()
        self.tvpaint_version = list(
            map(int, re.findall(r"\((\d+)\.(\d+)\)", self.metadata["Host"])[0])
        )


    def get_scene_tree(self, scene_index=0):
        """Returns scene-node.

        TODO: scenes might need their own class

        TODO: I don't have an example with multiple scenes, so the setup of the
        scenes-list is uncliear to me. For now I assume that scene_index=0 returns
        the first scene-item.

        """

        scenes_index = -1
        for idx, node in enumerate(self.root.children):
            if node.type == "scene":
                scenes_index = idx

        if scenes_index < 0:
            raise RuntimeError(
                "Project-tree does not have a 'scenes'-node. The tvp-version is probably unsupported"
            )
        return self.root.children[scenes_index:][scene_index]


    def get_clip_tree(self, scene_index=0, clip_index=0):
        """Return clip-node.

        TODO: I don't have an example with multiple scenes/clips, so the setup of the
        scenes&clips-list is unclear to me. For now I assume that scene_index=0 &
        clip_index=0 returns the first clip-item of the first scene.

        Args:
            scene_index(int)
            clip_index(int)

        Returns:
            Node():     a clip-node
        """
        return self.get_scene_tree(scene_index).children[1:][clip_index]


    def read_scene_metadata(self, scene_data):
        """Get scene info.

        Read it from disk, parse the data into a dict.

        Args:
            scene_data: a scene(Node)-object

        Returns:
            dict:   a dictionary with scene-info

        """
        # scene-info-node is the first child of a scene-Node
        scene = scene_data.children[0]

        with open(self.file_path, 'rb') as file_obj:
            d_offset = scene.data_offset
            size = scene.size
            file_obj.seek(d_offset,0)
            data = file_obj.read(size)

        return decoders.parse_utf16_dictdata(data)


    def read_project_metadata(self):
        project = self.root.children[0]
        with open(self.file_path, 'rb') as file_obj:
            d_offset = project.data_offset
            size = project.size
            file_obj.seek(d_offset,0)
            data = file_obj.read(size)

        info = decoders.parse_utf16_dictdata(data)
        # History (if present) data is obfuscated with rot13-method, so decrypt it:
        for k, v in info.items():
            if k.startswith("History"):
                changed = {k: codecs.encode(v, 'rot_13')}
                info.update(changed)
        return info


    def validate_header(self, headerdata):
        """ Check if the header is valid

        Returns:
            True, if the headerdata is valid
        """

        d = list(headerdata[10:16])
        if d in (
            [0x00, 0x0F, 0x1F, 0x02, 0x19, 0x1B],
            [0x00, 0x10, 0x5A, 0xAF, 0xAA, 0xAB],
        ):
            return True
        else:
            return False


    def printnode(self, node, indent=0):
        for c in node.children:
            print(
                "    " * indent,
                "%s, size=%d, offset=%d" % (c.type, c.size, c.data_offset),
            )
            self.printnode(c, indent + 1)


    def hext(self, dat):
        """format data so we can read it as hex."""

        return ["%02x" % h for h in dat]


    def _get_type(self, header):
        """Check headerdata and return type and if it is data or a container.

        Args:
            header(bytes):  four headerbytes

        Returns:
            str:    name of the Node-type
            bool:   If True the header is of a data-type, else a container-type
        """

        for _type, data in self.headers.items():
            if data['header'] == tuple(header[0:4]):
                return _type, data['is_data']

        return "", True


    def process(self, file_obj, node, indent=0):
        """Populate the node-tree.

        Recursively build a node-tree of the items and containers we find in the
        tvpaint-file. The node-tree will be our structure to retreive data from.

        Args:
            file_obj(_io.BufferedReader): a tvpaint-file-object
            node(Node): node-object
            indent(int): indentation for printing the depth of our node(debugging)
        """

        counter = 0
        header = file_obj.read(24)  # read header-bytes
        node.type, is_data = self._get_type(header)
        node.size = struct.unpack_from(">Q", header, 16)[0]
        if not node.type:
            logger.warning(f"Unknown header: {self.hext(header)}")
            file_obj.seek(node.size, 1)
            return

        # print treestructure as we process:
        logger.debug(f"{'----' * indent} {node.type} ({node.size} bytes)")

        counter = 0
        if not is_data:
            while counter < node.size:
                next_peek = file_obj.read(24)
                next_size =  struct.unpack_from(">Q", next_peek, 16)[0]
                file_obj.seek(-24, 1)
                if self.validate_header(next_peek):
                    counter += next_size + 24
                    new_node = Node()
                    node.add_child(new_node)
                    self.process(file_obj, new_node, indent + 1)
        else:
            node.data_offset = file_obj.tell()
            file_obj.seek(node.size, 1)
