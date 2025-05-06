""" The LayerData-class provides functions to process tvpaint-data

Issued under the "do what you like with it - I take no responsibility" licence                                                                                                                                                     
"""

import os
import sys
import zlib
import struct
import numpy as np
import cv2
from collections import OrderedDict
from pprint import pprint


class LayerData(object):
    def __init__(self, write_dir, width, height):
        self.write_dir = write_dir
        self.layers = OrderedDict()
        self.layer_img_index = 0
        self.current_layerid = -1
        self.layername = ""
        self.width = width
        self.height = height
        self.last_image = None
        self.background = (
            np.zeros(shape=(self.height, self.width, 3), dtype=float) + 0.5
        )

    def save_img(self, image_data, write_path):
        alpha = image_data[:, :, 3].astype(float) / 255
        fg = alpha[:, :, np.newaxis] * image_data[:, :, :3].astype(float) / 255
        bg = (1 - alpha[:, :, np.newaxis]) * self.background
        res = cv2.add(fg, bg)
        res = (res * 255).astype(np.uint8)
        cv2.imwrite(write_path, res, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

    def unpack_ZIP(self, zchk, offset=0):
        """Uncompress zip-data

        Args:
            zchk (bytes): zchk-data
            offset (int, optional): data-offset. Defaults to 0.

        Returns:
            bytes: Uncompressed data
        """
        multi = struct.unpack_from(">I", zchk, offset + 16)[0]
        offset += 20
        result = b""  # empty string of bytes
        for i in range(multi):
            offset += 4
            uncompr_size = struct.unpack_from(">I", zchk, offset)[0]
            offset += 4
            compr_size = struct.unpack_from(">I", zchk, offset)[0]
            offset += 4
            zblock = zchk[offset : offset + compr_size]  # read compressed block
            decomp = zlib.decompress(zblock)
            if len(decomp) != uncompr_size:
                raise ("decompsize is different than actual decompressed size!")
            result += decomp
            offset += compr_size
        return result

    def unpack_RLE(self, data):
        """Return imagedata from RLE-compressed data.

        Args:
            data: (bytes) a datablock
        Returns:
            list: RGBA data (8bit)
        """

        pixel_bytes = 4
        ret = []
        offset = 0
        while offset < len(data):
            code = struct.unpack_from("B", data, offset=offset)[0]
            if code <= 0x7B:  # <=123
                size = code + 1
                length = size * pixel_bytes
                result = tuple(data[offset + 1 : offset + length + 1])
                offset += length + 1
            elif code >= 0x85:  # >=133
                multiplier = 255 - code + 2
                result = tuple(data[offset + 1 : offset + pixel_bytes + 1]) * multiplier

                offset += pixel_bytes + 1
            else:
                print("offset", offset)
                if offset == len(data) - 1:
                    break
                else:
                    return None
            # print("adding:",  repr(result))
            sys.stdout.flush()
            ret.extend(result)
        return ret

    def process_DBOD(self, data):
        """decode DBOD-data which is RLE-compressed imagedata

        Args:
            data (_type_): _description_

        Returns:
            list: RGBA-data(8bit)

        """

        image_data = np.ndarray(
            shape=(self.height, self.width, 4),
            dtype=np.uint8,
            buffer=bytes(self.unpack_RLE(data)),
        )
        self.last_image = image_data
        filename = "layer{:03d}_{:03d}.jpg".format(
            self.current_layerid, self.layer_img_index
        )
        write_path = os.path.join(self.write_dir, filename)
        self.save_img(image_data, write_path)

    def process_SRAW(self, data):
        img = np.zeros(shape=(self.height, self.width, 4), dtype=np.uint8)
        offset = 0
        total_length = len(data)

        # first some header data:
        squaresize = struct.unpack_from(">I", data, offset=offset)[0]
        offset += 4
        if squaresize == 6:
            img = self.last_image
        else:
            y1 = 0
            y2 = squaresize
            x1 = 0
            x2 = squaresize

            thumbsize = struct.unpack_from(">I", data, offset=offset)[0]
            offset += 4
            _thumbdata = data[offset : offset + thumbsize]
            offset += thumbsize

            count = 1
            offset += 4
            while offset < total_length - 4:
                magicnumber = struct.unpack_from(">I", data, offset=offset)[0]
                _next_one = struct.unpack_from(">I", data, offset=offset + 4)[0]
                offset += 4

                # determine the size of the square
                if y2 > self.height:
                    squaresize_y = self.height % squaresize
                else:
                    squaresize_y = squaresize

                if x2 > self.width:
                    squaresize_x = self.width % squaresize
                else:
                    squaresize_x = squaresize

                # See if magicnumber means 'copy' or 'decode rle'.
                if magicnumber == 0:  # 'copy'
                    _from_frame = struct.unpack_from(">I", data, offset=offset)[0]
                    pick = struct.unpack_from(">I", data, offset=offset + 4)[0]
                    ly = ((pick * squaresize) // self.width) * squaresize
                    lx = (pick * squaresize) % self.width

                    for chan in range(0, 4):
                        img_dat = self.last_image[
                            ly : ly + squaresize_y, lx : lx + squaresize_x, :
                        ]
                    size = 8

                else:  # decode RLE
                    size = magicnumber
                    rle_data = data[offset : offset + size]
                    img_dat = self.unpack_RLE(rle_data)

                piece = np.ndarray(
                    shape=(squaresize_y, squaresize_x, 4),
                    dtype=np.uint8,
                    buffer=bytes(img_dat),
                )

                # add the piece(square) to the big picture
                for chan in range(0, 4):
                    img[y1:y2, x1:x2, chan] = piece[:, :, chan]

                x1 += squaresize
                x2 += squaresize
                if x1 >= self.width:
                    x1 = 0
                    x2 = squaresize
                    y1 += squaresize
                    y2 += squaresize

                offset += size
                count += 1
                size = 0
            self.last_image = img

        filename = "layer{:03d}_{:03d}.jpg".format(
            self.current_layerid, self.layer_img_index
        )
        write_path = os.path.join(self.write_dir, filename)
        self.save_img(img, write_path)

    def process_XS24(self, size, contents):
        a = struct.unpack_from(">H", contents, offset=0)[0]
        b = struct.unpack_from(">H", contents, offset=2)[0]
        length = struct.unpack_from(">I", contents, offset=4)[0]
        print(a, b, length)
        for i in range(0, a * b):
            if i % a == 0:
                print("====================")
            hx = ":".join(
                ["{:02x}".format(x) for x in contents[i * 3 + 8 : i * 3 + 11]]
            )
            dc = ":".join(
                ["{:03d}".format(x) for x in contents[i * 3 + 8 : i * 3 + 11]]
            )
            print("{}\t{}".format(hx, dc))

    def parse_utf8(self, dic, items):
        count = 0
        while True:
            item = items[count]
            if item == "":
                break
            if item[0] == "[" and item[-1] == "]":
                sectionname = item
                ret = self.parse_utf8({}, items[count + 1 :])
                dic[sectionname] = ret
                retlength = len(list(ret.items())) + 2
                count += retlength
            else:
                k, v = item.split("=")
                dic[k] = v
                count += 1
        return dic

    def process_LEXT(self, contents):
        v = bytearray(contents[3:]).decode("utf8").split("\n")
        res = self.parse_utf8({}, v)
        pprint(res)

    def process_UDAT(self, contents):
        """Process UDAT

        Is this Scribbledata?
        """

        udat_size = len(contents)
        offset = 16
        a = struct.unpack_from(">I", contents, offset=offset)[0]
        print("udat_a:", a)
        offset += 4
        b = struct.unpack_from(">I", contents, offset=offset)[0]
        print("udat_b:", b)
        offset += 4
        while offset < udat_size:
            # skip B2 etc
            offset += 16
            # 2 int's
            c = struct.unpack_from(">I", contents, offset=offset)[0]
            print("b2_01:", c)
            offset += 4
            sub_size = struct.unpack_from(">I", contents, offset=offset)[0]
            print("sub_size:", sub_size)
            offset += 4
            sub_data = contents[offset : offset + sub_size]
            offset += sub_size
            sub_offset = 0
            first = struct.unpack_from(">I", sub_data, offset=sub_offset)[0]
            print("sub_first:", first)
            sub_offset += 4
            if first > 0:
                while sub_offset < sub_size:
                    sub_a = struct.unpack_from(">I", sub_data, offset=sub_offset)[0]
                    print("sub_a", sub_a)
                    sub_offset += 4
                    sub_wordlength = (
                        struct.unpack_from(">H", sub_data, offset=sub_offset)[0]
                    ) * 2
                    print("wordlength:", sub_wordlength)
                    sub_offset += 2
                    stuff = sub_data[sub_offset : sub_offset + sub_wordlength]
                    print(bytearray(stuff).decode("utf-16be"))
                    sub_offset += sub_wordlength
                    sub_offset += 16  # ???
                    sub_offset += 52  # ????
                    sub_offset += 4  # 0 ?
                    sub_seclength = struct.unpack_from(
                        ">I", sub_data, offset=sub_offset
                    )[0]
                    sub_offset += 4

                    stuff = sub_data[sub_offset : sub_offset + sub_seclength]
                    print(bytearray(stuff).decode("utf-16be"))
                    sub_offset += sub_seclength
                    sub_offset += 20
                    sub_seclength = struct.unpack_from(
                        ">I", sub_data, offset=sub_offset
                    )[0]
                    sub_offset += 4
                    stuff = sub_data[sub_offset : sub_offset + sub_seclength]
                    print(bytearray(stuff).decode("utf-16be"))

    def process_LR(self, contents):
        for i in range(0, len(contents) // 2):
            n = struct.unpack_from(">H", contents, offset=i * 2)[0]
            print("{}\t{}".format(i, n))

    def process_XSHT(self, contents):
        pass

    def process_XSRC(self, contents):
        v = bytearray(contents[3:]).decode("utf8").split("\n")
        res = self.parse_utf8({}, v)
        pprint(res)

    def process_layers(self, dat, write_dir=""):
        dat.parse()
        result = []
        for ident, contents in dat.form_data:
            if not contents:
                continue
            self.process_datablock(ident, contents)

        return self.layers

    def process_datablock(self, ident, contents):
        """Select what to do, based upon ident."""
        if ident == "ZCHK":
            size = struct.unpack_from(">I", contents, offset=0)[0]
            unzipped = self.unpack_ZIP(contents)
            u_ident = "".join(
                map(chr, struct.unpack_from("BBBB", unzipped, offset=0))
            )  # char*4 identifier
            u_contents = unzipped[8 : 8 + size]
            self.process_datablock(u_ident, u_contents)

        if ident == "DBOD":
            self.process_DBOD(contents)
            self.layers[self.current_layerid]["images"].append(self.layer_img_index)
            self.layer_img_index += 1

        if ident == "SRAW":
            self.process_SRAW(contents)
            self.layers[self.current_layerid]["images"].append(self.layer_img_index)
            self.layer_img_index += 1

        if ident == "XS24":
            pass
            # process_XS24(size, contents)

        if ident == "LEXT":
            self.process_LEXT(contents)

        if ident == "UDAT":  # scribbledata?
            self.layer_img_index = -1
            # process_UDAT(contents)

        if ident == "LNAM":
            layername = bytearray(contents).decode("utf8")[:-1]
            self.current_layerid += 1
            self.layer_img_index = 0
            self.layers[self.current_layerid] = {"images": [], "name": layername}

        if ident == "XSRC":
            self.process_XSRC(contents)
        if ident == "XSHT":
            self.process_XSHT(contents)
        if ident == "LNAW":
            pass
        if ident == "XSRC":
            self.process_XSRC(contents)
        if ident == "STCK":
            pass
        if ident in ["LRHD", "LRSH", "LRSR"]:  # layer-settings?
            pass
