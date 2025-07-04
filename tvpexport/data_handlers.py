"""Provides handlers for various data-stuff like Clip, Layer, Image, etc.

Issued under the "do what you like with it - I take no responsibility" licence
"""

import sys
import struct
import numpy as np
# import cv2
from . import decoders
import logging

# setup logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class Clip(object):
    """Clip-object.

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
:
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
            scene_index=scene_index, clip_index=clip_index
        )
        self.metadata = self._read_clip_metadata(tvptree.file_path, clip_tree)
        with open(self.tvptree.file_path, "rb") as file_obj:
            self.read_clip_data(file_obj, clip_tree)

    @property
    def dloc(self):
        return self._dloc

    @dloc.setter
    def dloc(self, values):
        """ DLOC-data contains the dimesions of the clip.

        Args:
            values (_type_): _description_

        Returns:
            _type_: _description_
        """
        self.width = values[0]
        self.height = values[1]
        self._dloc = values
        return self._dloc

    def _read_clip_metadata(self, file_path, clip_tree):
        """ Read and parse the clip-metadata.
        Args:
            file_path (_type_): _description_
            clip_tree (_type_): _description_

        Returns:
            _type_: _description_
        """
        with open(file_path, "rb") as file_obj:
            d_offset = clip_tree.children[0].data_offset
            size = clip_tree.children[0].size
            file_obj.seek(d_offset, 0)
            data = file_obj.read(size)
        return decoders.parse_utf16_dictdata(data)

    def read_clip_data(self, file_obj, clip_tree):
        """_summary_

        Args:
            file_obj (_type_): _description_
            clip_tree (_type_): _description_
        """
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

            if size % 2:
                size += 1  # size has to be an even number!

            data = file_obj.read(size)
            logger.debug(f"{ident} = ({size} bytes), was read at pos: {offset}.")
            offset += size

            # clip-data:
            if ident == "DGBL":
                self.dgbl = decoders.decode_DGBL(data)
            if ident == "DPEL":
                self.dpel = decoders.decode_DPEL(data)
            if ident == "BGMD":
                self.bgmd = decoders.decode_BGMD(data)
            if ident == "DLOC":
                self.dloc = decoders.decode_DLOC(data)
            if ident == "ARAT":
                self.arat = decoders.decode_ARAT(data)
            if ident == "CRLR":
                self.crlr = decoders.decode_CRLR(data)
            if ident == "BGP1":
                self.bgp1 = decoders.decode_BGP1(data)
            if ident == "BGP2":
                self.bgp2 = decoders.decode_BGP2(data)
            if ident == "ANNO":
                self.anno = decoders.decode_ANNO(data)
            if ident == "FRAT":
                self.frat = decoders.decode_FRAT(data)
            if ident == "FILD":
                self.fild = decoders.decode_FILD(data)
            if ident == "MARK":
                self.mark = decoders.decode_MARK(data)
            if ident == "XSHT":
                self.xsht = decoders.decode_XSHT(data)
            if ident == "TLNT":
                self.tlnt = decoders.decode_TLNT(data)

            if ident == "LNAM":
                layer_index += 1  # LNAM is the first item of a layer, so up the index
                layer_name = decoders.decode_LNAM(data)
                new_layer = Layer(layer_name, self.width, self.height)
                self.layers.append(new_layer)

            if ident == "LRHD":
                self.layers[layer_index].settings = decoders.decode_LRHD(data)

            if ident == "LRSH":  # has a ctg-layer
                self.layers[layer_index].settings = decoders.decode_LRHD(data)

            if ident == "LRSR":  # it's a ctg-layer for layer above
                layer_index += 1
                new_layer = Layer(
                    self.layers[layer_index - 1].name, self.width, self.height
                )
                new_layer.settings = self.layers[layer_index - 1].settings
                new_layer.is_ctg = True
                self.layers.append(new_layer)

            if ident in ("ZCHK", "DBOD", "SRAW"):
                image_index = len(self.layers[layer_index].images)
                image = Image(ident, image_index, self.width, self.height)
                image.raw_data = data
                self.layers[layer_index].images.append(image)

            if ident == "LEXT":
                self.layers[layer_index].lext = decoders.decode_LEXT(data)


class Layer(object):
    """These are known datablocks of which a layer consists of:
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
        self.settings = {}

    def frame(self, index: int):
        """ Return a frame/image, given the index of the timeline
        
        Args:
            index (int): timeline-position (starts with 0)

        Returns:
            numpy.ndarray(): image-data
        """

        start_frame = self.settings["start_frame"]
        frame_index = index - start_frame
        if frame_index < 0 or frame_index >= len(self.images):
            return np.zeros(shape=(self.height, self.width, 4), dtype=np.uint8)
        else:
            return self.construct_image(frame_index)

    def construct_image(self, img_index):
        """ Retreive an image from the imagelist.

        Args:
            img_index (int): index of the image

        Returns:
            numoy.ndarray(): imagedata
        """
        image = self.images[img_index]

        while image.type != "DBOD" and image.first_info in (2, 6):
            if image.first_info == 2:
                image = self.images[image.second_info]
            if image.first_info == 6:
                image = self.images[image.index - 1]

        for tile in image.tiles:
            if image.type == "DBOD":
                tile_data = tile.data
            else:  # SRAW
                tile_data = self._resolve_tile_data(image, tile)

            # Debugging: print the index of the tile onto the tile.
            # tile_data[5:25, 1:50, :3] = (0,0,255)
            # tile_data[5:25, 1:50, 3] = 150
            # cv2.putText(
            #     tile_data, str(tile.index), (1,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA
            # )

            x = (tile.index * image.tile_size) % image.max_tilewidth
            y = (tile.index * image.tile_size) // image.max_tilewidth * image.tile_size
            image.result[y : y + tile_data.shape[0], x : x + tile_data.shape[1]] = tile_data

        return image.result

    def _resolve_tile_data(self, image, tile):
        """Resolve tile-data

        Args:
            image (Image()): Image()-object
            tile (ImageTile()): Tile()-object

        Raises:
            RuntimeError: 'Crash' when unknown image-header-data is discovered.
            So we can implement it, afterwards.

        Returns:
            numpy.ndarray(): tile-(image)data
        """

        tile.width = self.images[0].tiles[tile.index].width
        tile.height = self.images[0].tiles[tile.index].height

        if tile.type == "RAW":
            tile_data = tile.data

        elif tile.type == "RLE":
            tile_data = decoders.decode_DBOD(tile.rle_data, tile.width, tile.height)

        elif tile.type == "CPY":
            if tile.ref_local_tile == True:
                ref_local_tile_index = tile.lookup_tile_index
                ref_tile = image.tiles[ref_local_tile_index]

                if ref_tile.type == "CPY":
                    # If the locally referred tile is of type 'CPY', then Resolve
                    # further from previous image-tile(s)

                    if image.first_info == 6 or image.first_info == image.tile_size:
                        prev_image = self.images[image.index - 1]
                    elif image.first_info == 2:
                        prev_image = self.images[image.second_info]
                    else:
                        raise RuntimeError(f"Unknown 'First info': {image.first_info}")

                    prev_tile = prev_image.tiles[ref_local_tile_index]
                    tile_data = self._resolve_tile_data(prev_image, prev_tile)
                else:
                    # copy the image-data from local image
                    xpos = (ref_local_tile_index * image.tile_size) % image.max_tilewidth
                    ypos = (
                        ref_local_tile_index * image.tile_size // image.max_tilewidth
                    ) * image.tile_size
                    tile_data = image.result[
                        ypos : ypos + image.tile_size, xpos : xpos + image.tile_size
                    ].copy()

                # # Debugging: print local_tile_index onto the tile
                # tile_data[20:50, 1:50, :3] = (0, 255, 0)
                # tile_data[20:50, 1:50, 3] = 200
                # cv2.putText(
                #     tile_data, str(local_tile_index), (1,45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 2, cv2.LINE_AA
                # )
            else:

                if image.first_info == 6 or image.first_info == image.tile_size:
                    prev_image = self.images[image.index - 1]
                elif image.first_info == 2:
                    prev_image = self.images[image.second_info]
                else:
                    raise RuntimeError(f"Unknown 'First info': {image.first_info}")

                prev_tile = prev_image.tiles[tile.index]
                tile_data = self._resolve_tile_data(prev_image, prev_tile)

        return tile_data


class Image(object):
    def __init__(self, image_type, index, width, height, tile_size=64):
        self.type = image_type
        self.index = index
        self._raw_data = bytes()
        self.width = width
        self.height = height
        self._tiles = []
        self.tile_size = tile_size
        self._result = np.ndarray([])

        # set dimensions for calculating tile-positions, and data-slices.
        self.num_tiles_x = self.width // self.tile_size + int(
            self.width % self.tile_size > 0
        )
        self.num_tiles_y = self.height // self.tile_size + int(
            self.height % self.tile_size > 0
        )
        self.num_tiles = self.num_tiles_x * self.tile_size
        self.max_tilewidth = self.num_tiles_x * self.tile_size

    @property
    def result(self):
        """ This will store the final image-data(np.ndarray).
        It is empty when the class is initialized. Gets filled when accessed.

        """
        if not self._result.shape:
            self._result = np.zeros(shape=(self.height, self.width, 4), dtype=np.uint8)
        return self._result

    @property
    def raw_data(self):
        if self.type == "ZCHK":
            self._raw_data = decoders.decode_ZCHK(self._raw_data)
            self.type = bytes(struct.unpack_from("BBBB", self._raw_data)).decode(
                "ascii"
            )
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
        _trigger_unzip = self.first_info  # TODO: improve this
        if self.type == "DBOD":
            image_data = decoders.decode_DBOD(self.raw_data, self.width, self.height)
            for tile_index in range(0, self.num_tiles):
                tile = ImageTile("RAW", tile_index)
                xpos = (tile_index * self.tile_size) % self.max_tilewidth
                ypos = (
                    tile_index * self.tile_size // self.max_tilewidth * self.tile_size
                )
                tile.data = image_data[
                    ypos : ypos + self.tile_size, xpos : xpos + self.tile_size
                ]
                tile.width = tile.data.shape[1]
                tile.height = tile.data.shape[0]
                self._tiles.append(tile)

        if self.type == "SRAW":
            unpack_uint = struct.Struct('>I').unpack_from
            data_offset = 0
            total_length = len(self.raw_data)

            # We already assume tile_size is 64
            _tile_size = unpack_uint(self.raw_data, data_offset)[0]
            data_offset += 4

            thumb_size = unpack_uint(self._raw_data, data_offset)[0]
            data_offset += 4
            _thumbdata = self._raw_data[data_offset : data_offset + thumb_size]
            data_offset += thumb_size

            tile_amount = unpack_uint(self._raw_data, data_offset)[0]
            data_offset += 4
            for tile_index in range(tile_amount):
                tile = ImageTile("", tile_index)
                magicnumber = unpack_uint(self.raw_data, data_offset)[0]
                data_offset += 4
                if magicnumber == 0:
                    tile.type = "CPY"
                    tile.ref_local_tile = not bool(
                        unpack_uint(self.raw_data, data_offset)[0]
                    )

                    data_offset += 4
                    tile.lookup_tile_index = unpack_uint(self.raw_data, data_offset)[0]
                    data_offset += 4

                else:
                    tile.type = "RLE"
                    size = magicnumber
                    tile.rle_data = self.raw_data[data_offset : data_offset + size]
                    data_offset += size

                self._tiles.append(tile)


class ImageTile(object):
    """An imagetile is a piece of an image.

    Tvpaint stores imagedata(SRAW) as tiles (mostly 64x64 pixels).
    """

    def __init__(self, type_name, index):
        self.index = index
        self.type = type_name
        self.ref_local_tile = False
        self.lookup_tile_index = 0
        self.width = 0
        self.height = 0
        self.rle_data = bytes()
        self._data = np.ndarray([])

    @property
    def data(self):
        if self.rle_data and self._data.size == 0:
            self._data = decoders.decode_DBOD(self.rle_data, self.width, self.height)
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
