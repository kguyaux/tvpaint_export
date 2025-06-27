""" Decoders for various blocks of data.


"""
import logging
import os
import struct
import sys
import uuid
import zlib

import numpy as np

# setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

BYTEDUMP_DIR="_bytes_dump_"


################################################################
##                                                            ##
##                   DECORATORS                               ##
##                                                            ##
################################################################

def bypass(func):
    """ A helper-decorator to bypass a function.

    Handy for data-processorfunctions that are not finished yet, or not needed
    because we are testing other stuff..
    """
    def wrapper(*args, **kwargs):
        logger.debug(f"Function '{func.__name__}' was bypassed..")
    return wrapper

def print_bytes(func):
    """ A helper-decorator to print the bytes in hex.
    """
    def wrapper(*args, **kwargs):
        data = args[1]
        logger.debug(f"{data}")
    return wrapper

def dump_bytes(with_uid=False):
    """
    A helper-decorator that bypasses the processorfunction but dumps the contents(bytes)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # object = args[0]
            contents = args[0]
            print(f"Function '{func.__name__}' bytes were dumped.")
            if with_uid:
                uniq = "_" + uuid.uuid4().hex[:8]
            else:
                uniq = ""
            with open(
                os.path.join(
                    BYTEDUMP_DIR,
                    func.__name__.lower() + uniq + ".bin"
                ),
            "wb") as dumpfile:
                dumpfile.write(contents)
        return wrapper
    return decorator


################################################################
##                                                            ##
##                     TEXT-PARSERS                           ##
##                                                            ##
################################################################

def parse_dict(dic: dict, items: list):
    """ Parse utf8-based dict-data to dict.

    """
    count = 0
    while True:
        item = items[count]
        if item == "":
            break
        if item[0] == "[" and item[-1] == "]":
            sectionname = item
            ret = parse_dict({}, items[count + 1 :])
            dic[sectionname] = ret
            retlength = len(list(ret.items())) + 2
            count += retlength
        else:
            if "=" not in item:
                break
            key, value = item.split("=")
            dic[key] = value
            count += 1
    return dic


def parse_utf16_dictdata(data: bytes):
    """Parse data that contains a utf16-textbased dictionary.

    Args:
        data(bytes)

    Returns:
        dict
    """
    offset = 0
    fieldcount = struct.unpack_from(">I", data, offset)[0]
    offset += 4
    amount = fieldcount * 2
    count = 0
    i = []
    while count < amount:
        # '<H' stands for bigendian unsigned short(16bit))
        s = struct.unpack_from(">H", data, offset)
        length = int(s[0])
        offset += 2  # size of '>H'
        str_fmt = ">" + "H" * length
        string = bytes(data[offset : offset + (length * 2)]).decode("utf-16be")
        offset += struct.calcsize(str_fmt)
        count += 1
        i.append(string)
    return dict(zip(i[::2], i[1::2]))


################################################################
##                                                            ##
##                     MISC.                                  ##
##                                                            ##
################################################################

def unpack_RLE(data):
    """Return imagedata from RLE-compressed data.

    Args:
        data: (bytes) a datablock
    Returns:
        bytearray(): RGBA data (8bit)
    """
    pixel_bytes = 4
    unpacked = bytearray()
    offset = 0
    while offset < len(data):
        _byte = struct.unpack_from("B", data, offset=offset)[0]
        if _byte <= 0x7B:  # <=123
            size = _byte + 1
            length = size * pixel_bytes
            result = data[offset + 1 : offset + length + 1]
            offset += length + 1
        elif _byte >= 0x85:  # >=133
            multiplier = 255 - _byte + 2
            result = data[offset + 1 : offset + pixel_bytes + 1] * multiplier
            offset += pixel_bytes + 1
        else:
            if offset == len(data) - 1:
                break
        unpacked.extend(result)
    return unpacked

################################################################
##                                                            ##
##                   LAYER DECODERS                           ##
##                                                            ##
################################################################
def decode_LNAM(data: bytes):

    """ LNAM contains the layername (utf8) """
    return data.partition(b'\x00')[0].decode("utf8")


def decode_LNAW(data: bytes):
    """ LNAM also contains the layername (utf8) """
    return data.partition(b'\x00')[0].decode("utf8")


def decode_LRHD(data: bytes):
    """ LRHD-data contains layer-settings.

    Visibility, locking, masking, comp-settings, etc
    LRHD-data is always 104 bytes

    TODO: check word-lengths
    """
    settings = []
    for i in range(0, len(data) // 2):
        setting = struct.unpack_from(">H", data, offset=i * 2)[0]
        settings.append(setting)

    return {
        "num_images": settings[7],
        "start_frame": settings[3],
        "end_frame": settings[5],
        "transperency": settings[9],
        "visible": bool(settings[15] & 0b00000001),
        "locked": bool(settings[15] & 0b00010000),
    }


def decode_LEXT(data: bytes):
    """ LEXT: storage of image UID's

    """
    v = bytearray(data[3:]).decode("utf8").split("\n")
    return parse_dict({}, v)


def decode_ZCHK(data: bytes):
    """ ZCHK-data is zipped data

    Returns: unzipped data

    Args:
        zchk (bytes): zchk-data

    Returns:
        bytearray: Uncompressed data

    """
    offset = 0
    num_blocks = struct.unpack_from(">I", data, 16)[0]
    offset += 20
    result = bytearray()
    for _i in range(num_blocks):
        offset += 4
        _uncompr_size = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        compr_size = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        zblock = data[offset : offset + compr_size]  # read compressed block
        decomp = zlib.decompress(zblock)
        result += decomp
        offset += compr_size
    return result


def decode_DBOD(data: bytes, image_width: int, image_height: int):
    """ Decode DBOD-data which is RLE-compressed imagedata

    Args:
        data (bytearray): unpacked imagedata

    Returns:
        np.ndarray: imagedata
    """
    imgdat = unpack_RLE(data)
    return np.ndarray(
        shape=(
            image_height,
            image_width,
            4
        ),
        dtype=np.uint8,
        buffer=imgdat
    )

@bypass
def decode_UDAT(contents: bytes):
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

################################################################
##                                                            ##
##                    CLIP DECODERS                           ##
##                                                            ##
################################################################

@bypass
def decode_XS24(contents):
    """ Unknown

    Thumbnaildata?

    """
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

def decode_DGBL(contents):
    """Unknown"""
    pass

def decode_DPEL(contents):
    """Unknown"""
    pass

def decode_DLOC(data):
    return struct.unpack_from(">HHHH", data)

def decode_BGMD(contents):
    """Unknown"""
    pass

def decode_ARAT(contents):
    """Unknown"""
    pass

def decode_CRLR(contents):
    """Unknown"""
    pass

def decode_BGP1(data):
    return struct.unpack_from("BBBB", data)


def decode_BGP2(data):
    """ Backgroundcolorpattern 2"""
    return struct.unpack_from("BBBB", data)


def decode_ANNO(contents):
    """Unknown"""
    pass

def decode_FRAT(contents):
    """Unknown"""
    pass

def decode_FILD(contents):
    """Unknown"""
    pass

def decode_MARK(contents):
    """Unknown"""
    pass

def decode_XSHT(contents):
    """Unknown"""
    pass

def decode_TLNT(contents):
    """Unknown"""
    pass

def decode_SPAR(contents):
    """Unknown"""
    pass

def decode_STCK(contents):
    """Unknown"""
    pass

def decode_XSRC(contents):
    """Unknown"""
    v = bytearray(contents[3:]).decode("utf8").split("\n")
    return parse_dict({}, v)

def decode_FCFG(contents):
    """Unknown"""
    pass
