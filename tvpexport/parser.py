"""Create a datastructure from a tvpaintfile.

From this structure we can extract data, to analyze and process.
It loads everything in memory, so that is not very optimal yet.
But for now that is good enough to get to learn the format.

Just create the `TVPTree`-class and use the `root`-attr(list) to access the data.
See the tvpexport-demo.py -example.

Issued under the "do what you like with it - I take no responsibility" licence.
"""

from array import array
import struct


class Node(object):
    def __init__(self, header, name):
        self.name = name
        self.size = struct.unpack_from(">Q", header, 16)[0]
        self.header = header
        self.data = None
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def add_data(self, data):
        self.data = data

    def parse_info(self):
        return [None]


class Utf_8(Node):
    def __init__(self, *args):
        super().__init__(*args)

    def _parse(self, dic, items):
        count = 0
        while True:
            item = items[count]
            if item == "":
                break
            if item[0] == "[" and item[-1] == "]":
                sectionname = item
                ret = self._parse({}, items[count + 1 :])
                dic[sectionname] = ret
                retlength = len(list(ret.items())) + 2
                count += retlength
            else:
                k, v = item.split("=")
                dic[k] = v
                count += 1
        return dic

    def parse_info(self):
        v = bytearray(self.data[3:]).decode("utf8").split("\n")
        return self._parse({}, v)


class Utf_16(Node):
    def __init__(self, *args):
        super().__init__(*args)

    def parse_info_generator(self, offset, fieldcount):
        # unpack the info strings (each char is a 16bit unsigned big-endian)
        amount = fieldcount * 2
        count = 0
        while count < amount:
            # '<H' stands for bigendian unsigned short(16bit))
            s = struct.unpack_from(">H", self.data, offset)
            length = int(s[0])
            offset += 2  # size of '>H'
            str_fmt = ">" + "H" * length
            string = bytes(self.data[offset : offset + (length * 2)]).decode("utf-16be")
            offset += struct.calcsize(str_fmt)
            count += 1
            yield string

    def parse_info(self):
        offset = 0
        fieldcount = struct.unpack_from(">I", self.data, offset)[0]
        offset += 4
        i = self.parse_info_generator(offset, fieldcount)
        return dict(zip(i, i))


class Thumb(Node):
    def __init__(self, *args):
        super().__init__(*args)


class Project(Node):
    def __init__(self, *args):
        super().__init__(*args)


class ClipData(Node):
    def __init__(self, *args):
        super().__init__(*args)
        self.form_data = []

    def parse(self):
        x = struct.unpack_from("BBBB", self.data, 0)
        self.blockname = bytes(x).decode("utf8")
        self.blocksize = struct.unpack_from(">I", self.data, 4)[0]
        offset = 12
        while offset < self.blocksize:
            name = bytes(struct.unpack_from("BBBB", self.data, offset)).decode("ascii")
            size = struct.unpack_from(">I", self.data, offset + 4)[0]
            blockdata = self.data[offset + 8 : offset + 8 + size]
            self.form_data.append((name, blockdata))
            offset += size + 8
            if offset < self.blocksize and self.data[offset] == 0:
                offset += 1


class TvpTree(object):
    def __init__(self, filepath):
        self.seek = 0
        self.data = self.load_whole(filepath)
        projectheader = self.data[self.seek : 24]
        self.root = self.create_node(projectheader)
        self.process(self.root)

    def load_whole(self, filepath):
        print("reading..")
        # chunksize = 3276000
        data = array("B", b"")
        with open(filepath, "rb") as source:
            while True:
                chunk = array("B", source.read(3276000))
                if not chunk:
                    break
                data.extend(chunk)
        return data

    def is_header(self, dat):
        d = list(dat[10:16])
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
                "\t" * indent,
                "%s [%02x %02x] (%d)" % (c.name, c.header[8], c.header[9], c.size),
            )
            self.printnode(c, indent + 1)

    def create_node(self, header):
        hh = tuple(header[0:4])
        if hh == (0x33, 0x84, 0x78, 0x0E):
            return Project(header, "project")
        if hh == (0x33, 0x85, 0x55, 0x3A):
            return Utf_16(header, "project-info")
        if hh == (0x33, 0x8C, 0x4E, 0xE4):
            return Node(header, "thumbnail")
        if hh == (0x33, 0x8A, 0x96, 0x08):
            return Utf_16(header, "thumbnail-info")
        if hh == (0x33, 0x8B, 0x71, 0x54):
            return Thumb(header, "thumbnail-data")
        if hh == (0x04, 0x56, 0x69, 0x28):
            return Utf_8(header, "sound-data")
        if hh == (0x33, 0x8E, 0x0A, 0xEA):
            return Utf_8(header, "label-data")
        if hh == (0x33, 0xFB, 0x9B, 0xE6):
            return Node(header, "zeros")
        if hh == (0xE5, 0xC8, 0xE0, 0x7A):
            return Node(header, "object")
        if hh == (0xE5, 0xCA, 0xDE, 0xAC):
            return Utf_8(header, "object")
        if hh == (0xE5, 0xCB, 0x5E, 0x68):
            return Utf_16(header, "object-info")
        if hh == (0x33, 0x86, 0x31, 0xB2):
            return Node(header, "shot")
        if hh == (0x33, 0x88, 0xDA, 0x98):
            return Utf_16(header, "shot-info")
        if hh == (0x33, 0x89, 0xB8, 0x46):
            return Node(header, "clip")
        if hh == (0x33, 0x87, 0xE3, 0x4A):
            return Utf_16(header, "clip-info")
        if hh == (0x33, 0x87, 0x11, 0x54):
            return ClipData(header, "clip-data")

        # return unknown
        return Node(header, "%02x %02x %02x %02x" % hh)

    def process(self, node):
        counter = 0
        child = None
        while counter < node.size:
            counter += 24
            nextpeek = self.data[self.seek + 24 : self.seek + 48]
            if self.is_header(nextpeek):
                child = self.create_node(nextpeek)
                node.add_child(child)
                self.seek += 24
                counter += self.process(child)
            else:
                start = self.seek + 24
                end = self.seek + 24 + node.size
                node.add_data(self.data[start:end])
                self.seek += node.size
                break
        return node.size
