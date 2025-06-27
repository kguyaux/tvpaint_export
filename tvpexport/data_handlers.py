""" The LayerData-class provides functions to process tvpaint-data

Issued under the "do what you like with it - I take no responsibility" licence
"""

import sys
import struct
import numpy as np
import cv2
from . import decoders
import logging

# setup logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class Clip(object):
    """ Clip-object.

    A clip-object holds the layers with image(sequence)data

    In the tvpaint-format the data is stored by ID's, in this order:

    clip-intro:
        XS24  Thumbnail
        DGBL
        DPEL
        DLOC
        BGMD
        ARAT
        CRLR
        BGP1
        BGP2
        ANNO
        FRAT
        FILD
        MARK
        XSHT  Xsheet(?)
        TLNT  80 bytes of ?
        SPAR  ?

    layer ( * n):
        LNAM  layername
        LNAW  layername
        LRHD
        ZCHK  zipped imagedata (DBOD or SRAW)
        DBOD  First imagedata, full image RLE-encoded
        SRAW  imagedata related to DBOD, pieces of RLE-encoded ata
        LEXT  image uids
        UDAT  scribbledata?

    rest if the clip id's:
        STCK
        XSRC
        FCFG
    """

    def __init__(self, tvptree, scene_index=0, clip_index=0):
        self.tvptree = tvptree
        self.layers = []
        self.width = 0
        self.height = 0
        self._dloc = ()
        self.arat = ()
        self.bgp1 = ()
        self.bgp2 = ()
        clip_tree = tvptree.get_clip_tree(
            scene_index=scene_index,
            clip_index=clip_index
        )
        self.metadata = self._read_clip_metadata(tvptree.file_path, clip_tree)
        # self.clip_index_data = self.build_clip_data_index(tvptree.file_path, clip_tree)
        with open(self.tvptree.file_path, 'rb') as file_obj:
            self.read_clip_data(file_obj, clip_tree)

    @property
    def dloc(self):
        return self._dloc

    @dloc.setter
    def dloc(self, values):
        self.width = values[0]
        self.height = values[1]
        self._dloc = values
        return self._dloc

    def _read_clip_metadata(self, file_path, clip_tree):
        """ Read and parse the clip-metadata. """
        with open(file_path, 'rb') as file_obj:
            d_offset = clip_tree.children[0].data_offset
            size = clip_tree.children[0].size
            file_obj.seek(d_offset,0)
            data = file_obj.read(size)
        return decoders.parse_utf16_dictdata(data)


    def read_clip_data(self, file_obj, clip_tree):

        d_offset = clip_tree.children[1].data_offset
        size = clip_tree.children[1].size
        file_obj.seek(d_offset, 0)

        header_bytes = file_obj.read(12)
        offset = 12
        form_name = bytes(struct.unpack_from("BBBB", header_bytes, 0)).decode("ascii")
        form_size = struct.unpack_from(">I", header_bytes, 4)[0]
        tvpp_name = bytes(struct.unpack_from("BBBB", header_bytes, 8)).decode("ascii")

        logger.debug(f"{form_name}, {form_size} {tvpp_name}")
        layer_index = -1
        while offset < form_size:
            header_bytes = file_obj.read(8)

            ident = bytes(struct.unpack_from("BBBB", header_bytes, 0)).decode("ascii")
            size = struct.unpack_from(">I", header_bytes, 4)[0]
            offset += 8

            if (size % 2):
                size = int(size + (size % 2))  # size has to be an even number!

            data = file_obj.read(size)
            logger.debug(f"{ident} = ({size} bytes), was read at pos: {offset}.")
            offset += size

            # clip-data:
            if ident == 'DLOC':
                self.dloc = decoders.decode_DLOC(data)
            if ident == 'ARAT':
                self.arat = decoders.decode_ARAT(data)
            if ident == 'BGP1':
                self.bgp1 = decoders.decode_BGP1(data)
            if ident == 'BGP2':
                self.bgp2 = decoders.decode_BGP2(data)

            if ident == "LNAM":
                layer_index += 1  # LNAM is the first item of a layer, so up the index
                layer_name = decoders.decode_LNAM(data)
                print(repr(layer_name))
                new_layer = Layer(layer_name, self.width, self.height)
                self.layers.append(new_layer)

            if ident == "LRHD":
                self.layers[layer_index].settings = decoders.decode_LRHD(data)

            if ident == "LRSH":  # has a ctg-layer
                self.layers[layer_index].settings = decoders.decode_LRHD(data)

            if ident == "LRSR":  # it's a ctg-layer for layer above
                layer_index += 1
                new_layer = Layer(self.layers[layer_index - 1].name, self.width, self.height)
                new_layer.settings = self.layers[layer_index - 1].settings
                new_layer.is_ctg = True
                self.layers.append(new_layer)

            if ident in ('ZCHK', 'DBOD', 'SRAW'):
                image_index = len(self.layers[layer_index].images)
                image = Image(ident, image_index, self.width, self.height)
                image.raw_data = data
                self.layers[layer_index].images.append(image)

            if ident == "LEXT":
                self.layers[layer_index].lext = decoders.decode_LEXT(data)


class Layer(object):
    """ These are known datablocks of which a layer consists of:
        LNAM  layername
        LNAW  layername
        LRHD  layer-settings
        ZCHK  zipped imagedata (DBOD or SRAW)
        DBOD  First imagedata, full image RLE-encoded
        SRAW  imagedata related to DBOD, pieces of RLE-encoded ata
        LEXT  image uids
        UDAT  scribbledata(?)
    """

    def __init__(self, name, width, height):
        self.name = name
        self.is_ctg = False
        self.images = []
        self.width = width
        self.height = height

    def frame(self, index):
        start_frame = self.settings['start_frame']
        frame_index = index - start_frame
        if frame_index < 0 or frame_index >= len(self.images):
            return np.zeros(shape=(self.height, self.width, 4), dtype=np.uint8)
        else:
            return self.construct_image(frame_index)


    def construct_image(self, img_index):
        result_img = np.zeros(shape=(self.height, self.width, 4), dtype=np.uint8)
        image = self.images[img_index]

        while image.type != "DBOD" and image.first_info in (2,6):
            if image.first_info == 2:
                image = self.images[image.second_info]
            elif image.first_info == 6:
                image = self.images[image.image_index - 1]
            else:
                pass

        num_tiles_x = (self.width // image.tile_size + int(image.width % image.tile_size > 0))
        xwidth = num_tiles_x * image.tile_size

        for tile_index, tile in enumerate(image.tiles):

            if image.type != "DBOD":
                tile.width = self.images[0].tiles[tile_index].width
                tile.height = self.images[0].tiles[tile_index].height

            x = (tile_index * image.tile_size ) % xwidth
            y = ((tile_index * 64) // xwidth) * image.tile_size
            if tile.type == "RAW":
                tile_data = tile.data

            elif tile.type == "RLE":
                tile_data = decoders.decode_DBOD(tile.rle_data, tile.width, tile.height)

            elif tile.type == "CPY":
                # traverse back to previous imagetiles
                i = img_index
                if tile.ref_local_tile == False:
                    while i > 0:
                        i -= 1  # previous image
                        if self.images[i].first_info == 6:
                            continue
                        if self.images[i].first_info == 2:
                            i = self.images[i].second_info
                            continue

                        prev_tile = self.images[i].tiles[tile_index]
                        if prev_tile.type == "CPY":
                            if prev_tile.ref_local_tile:
                                diverted_tile = self.images[i].tiles[prev_tile.lookup_tile_index]
                                if diverted_tile.type == "CPY":
                                    tile_index = prev_tile.lookup_tile_index
                                    continue
                                else:
                                    tile_data = diverted_tile.data
                            else:
                                continue
                        if prev_tile.type == "RAW":
                            tile_data = prev_tile.data
                            break
                        if prev_tile.type == "RLE":
                            tile_data = decoders.decode_DBOD(prev_tile.rle_data, tile.width, tile.height)
                            break

                if tile.ref_local_tile == True:
                    local_tile_index = tile.lookup_tile_index
                    xpos = ((local_tile_index * image.tile_size) % xwidth)
                    ypos = (local_tile_index * image.tile_size // xwidth ) * image.tile_size
                    tile_data = result_img[ypos: ypos + image.tile_size, xpos:xpos + image.tile_size].copy()

            else:
                raise RuntimeError(f"No tile of type: '{tile.type}'")


            if False:
                tile_data[5:25, 1:50, :3] = (0,0,255)
                tile_data[5:25, 1:50, 3] = 150
                cv2.putText(
                    tile_data, str(tile_index), (1,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA
                )

            result_img[y: y + tile_data.shape[0], x:x + tile_data.shape[1]] = tile_data

        return result_img


class Image(object):
    def __init__(self, image_type, image_index, width, height, tile_size=64):
        self.type = image_type
        self.image_index = image_index
        self._raw_data = bytes()
        self.width = width
        self.height = height
        self.sraw_repeat = False
        self._tiles = []
        self.tile_size = tile_size

    @property
    def raw_data(self):
        if self.type == "ZCHK":
            self._raw_data = decoders.decode_ZCHK(self._raw_data)
            self.type = bytes(struct.unpack_from("BBBB", self._raw_data)).decode('ascii')
            del self._raw_data[:8]
        return self._raw_data

    @raw_data.setter
    def raw_data(self, value):
        self._raw_data = value

    @property
    def first_info(self):
        return struct.unpack_from(">I", self.raw_data, 0)[0]

    @property
    def second_info(self):
        return struct.unpack_from(">I", self.raw_data, 4)[0]

    @property
    def third_info(self):
        return struct.unpack_from(">I", self.raw_data, 8)[0]

    @property
    def tiles(self):
        if not self._tiles:
            self.create_tiles()
        return self._tiles

    def create_tiles(self):
        trigger_unzip = self.first_info  # TODO: improve this
        num_tiles_x = (self.width // self.tile_size + int(self.width % self.tile_size > 0))
        num_tiles_y = (self.height // self.tile_size + int(self.height % self.tile_size > 0))
        num_tiles = num_tiles_x * num_tiles_y
        xwidth = num_tiles_x * self.tile_size

        if self.type == "DBOD":
            image_data = decoders.decode_DBOD(self.raw_data, self.width, self.height)
            for tile_index in range(0, num_tiles):
                tile = ImageTile("RAW")
                xpos = ((tile_index * self.tile_size) % xwidth)
                ypos = tile_index * self.tile_size // xwidth * self.tile_size
                tile.data = image_data[ypos:ypos + self.tile_size, xpos:xpos + self.tile_size]
                tile.width = tile.data.shape[1]
                tile.height = tile.data.shape[0]
                self._tiles.append(tile)


        if self.type == "SRAW":

            data_offset = 0
            total_length = len(self.raw_data)

            tile_size = struct.unpack_from(">I", self.raw_data, data_offset)[0]
            data_offset += 4
            # print("TS", tile_size)

            thumb_size = struct.unpack_from(">I", self._raw_data, data_offset)[0]
            data_offset += 4
            # print("THUMBSize", thumb_size)
            _thumbdata = self._raw_data[data_offset : data_offset + thumb_size]
            data_offset += thumb_size
            # print(data_offset)
            tile_index = 0
            tile_amount = struct.unpack_from(">I", self._raw_data, data_offset)[0]
            # print("tile_amount", tile_amount)
            data_offset += 4
            while data_offset < total_length - 4:
                tile = ImageTile("")
                magicnumber = struct.unpack_from(">I", self.raw_data, data_offset)[0]
                data_offset += 4
                if magicnumber == 0:
                    tile.type = "CPY"
                    tile.ref_local_tile = not bool(struct.unpack_from(">I", self.raw_data, data_offset)[0])

                    data_offset += 4
                    tile.lookup_tile_index = struct.unpack_from(">I", self.raw_data, data_offset)[0]
                    data_offset += 4

                else:
                    tile.type = "RLE"
                    size = magicnumber
                    tile.rle_data = self.raw_data[data_offset : data_offset + size]
                    data_offset += size

                self._tiles.append(tile)
                # print("tile", tile_index, tile.type, data_offset, total_length)
                tile_index += 1


    # def create_tiles(self, image_data, w, h, tile_size = 64):
    #     """ Generate tiles of the image_data.

    #     Args:

    #     Returns:

    #     """
    #     self.tiles = []
    #     self.set_canvas_size(64, w, h)
    #     num_tiles_y = (h // tile_size + int(h % tile_size > 1))
    #     num_tiles_x = (w // tile_size + int(w % tile_size > 1))
    #     ww = num_tiles_x * tile_size
    #     hh = num_tiles_y * tile_size
    #     self.size = (ww, hh)
    #     num_tiles = num_tiles_y * num_tiles_x
    #     for tile_index in range(0, num_tiles):
    #         tile = ImageTile("RAW")
    #         xpos = ((tile_index * tile_size) % ww)
    #         ypos = tile_index * tile_size // ww * tile_size
    #         tile.data = image_data[ypos:ypos + tile_size, xpos:xpos + tile_size]
    #         tile.width = image_data.shape[1]
    #         tile.height = image_data.shape[0]
    #         self.tiles.append(tile)

    # def from_tiles(self, w, h, tile_size=64):
    #     height = (h // tile_size + int(h % tile_size > 1)) * tile_size
    #     width = (w // tile_size + int(w % tile_size > 1)) * tile_size
    #     self.size = (width, height)

    #     result_img = np.zeros(shape=(height, width, 4), dtype=np.uint8)
    #     # num_tiles = height * width
    #     for tile_index in range(0, len(self.tiles)):
    #         tile = self.tiles[tile_index]
    #         x = (tile_index * tile_size ) % width
    #         # print(x)
    #         y = ((tile_index * tile_size) // width) * tile_size

    #         if tile.type == "RAW":
    #             image_data = tile.data
    #         elif tile.type == "RLE":
    #             decoded = unpack_RLE(tile.rle_data)
    #             image_data = np.ndarray(
    #                 shape=(tile.height, tile.width, 4),
    #                 dtype=np.uint8,
    #                 buffer=decoded
    #             )
    #         else:
    #             raise RuntimeError(f"Unknown tile-type: '{tile.type}'")

    #         if image_data.shape != (tile_size, tile_size):
    #             square = np.zeros(shape=(tile_size, tile_size, 4), dtype=np.uint8)
    #             square[:image_data.shape[0], :image_data.shape[1]] = image_data
    #             result_img[y: y + tile_size, x:x + tile_size] = square
    #         else:
    #             result_img[y: y + tile_size, x:x + tile_size] = image_data

    #     return result_img





class ImageTile(object):
    """ An imagetile is a piece of an image.

    Tvpaint stores imagedata as tiles (mostly 64x64 pixels). I think for memory-efficient
    storage..
    """
    def __init__(self, type_name, initial_data=None):
        self.type = type_name

        self.ref_local_tile = False
        self.lookup_tile_index = 0
        self.width = 0
        self.height = 0
        self.rle_data = bytearray()
        self._data = None
        if initial_data is not None:
            self.data = initial_data # Use the setter for initial assignment

    @property
    def data(self):
        """
        Getter for the image_data attribute.
        """
        if self.rle_data:
            self._data = decoders.decode_DBOD(self.rle_data, self.width, self.height)
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @data.setter
    def data(self, new_data):
        """
        Setter for the image_data attribute.
        Raises an error if the new_data is not a np.ndarray.
        """
        if not isinstance(new_data, np.ndarray):
            raise TypeError(
                f"Image data must be a numpy.ndarray, but got {type(new_data)} instead."
            )
        self._data = new_data



