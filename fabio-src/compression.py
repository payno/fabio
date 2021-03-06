# coding: utf-8
#
#    Project: X-ray image reader
#             https://github.com/kif/fabio
#
#
#    Copyright (C) European Synchrotron Radiation Facility, Grenoble, France
#
#    Principal author:       Jérôme Kieffer (Jerome.Kieffer@ESRF.eu)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Authors: Jérôme Kieffer, ESRF
         email:jerome.kieffer@esrf.fr

FabIO library containing compression and decompression algorithm for various
"""
# get ready for python3
from __future__ import absolute_import, print_function, with_statement, division
__author__ = "Jérôme Kieffer"
__contact__ = "jerome.kieffer@esrf.eu"
__license__ = "GPLv3+"
__date__ = "30/10/2015"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"


import sys
import base64
import hashlib
import struct
import logging
logger = logging.getLogger("compression")

try:
    import six
    if tuple(int(i) for i in six.__version__.split(".")[:2]) < (1, 8):
        raise ImportError("Six version is too old")
except ImportError:
    from .third_party import six


if six.PY2:
    bytes = str

import numpy

try:
    if sys.version_info < (2, 7):
        from .third_party import gzip
    else:
        import gzip
except ImportError:
    logger.error("Unable to import gzip module: disabling gzip compression")
    gzip = None

try:
    import bz2
except ImportError:
    logger.error("Unable to import bz2 module: disabling bz2 compression")
    bz2 = None

try:
    import zlib
except ImportError:
    logger.error("Unable to import zlib module: disabling zlib compression")
    zlib = None


def md5sum(blob):
    """
    returns the md5sum of an object...
    """
    return base64.b64encode(hashlib.md5(blob).digest())


def endianness():
    """
    Return the native endianness of the system
    """
    if numpy.little_endian:
        return "LITTLE_ENDIAN"
    else:
        return "BIG_ENDIAN"


def decGzip(stream):
    """

    Decompress a chunk of data using the gzip algorithm from Python or alternatives if possible

    """

    if gzip is None:
        raise ImportError("gzip module is not available")
    fileobj = six.BytesIO(stream)
    try:
        rawData = gzip.GzipFile(fileobj=fileobj).read()
    except IOError:
        logger.warning("Encounter the python-gzip bug with trailing garbage, trying subprocess gzip")
        try:
            # This is as an ugly hack against a bug in Python gzip
            import subprocess
            sub = subprocess.Popen(["gzip", "-d", "-f"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            rawData, err = sub.communicate(input=stream)
            logger.debug("Gzip subprocess ended with %s err= %s; I got %s bytes back" % (sub.wait(), err, len(rawData)))
        except Exception as error:  # IGNORE:W0703
            logger.warning("Unable to use the subprocess gzip (%s). Is gzip available? " % error)
            for i in range(1, 513):
                try:
                    fileobj = six.BytesIO(stream[:-i])
                    rawData = gzip.GzipFile(fileobj=fileobj).read()
                except IOError:
                    logger.debug("trying with %s bytes less, doesn't work" % i)
                else:
                    break
            else:
                logger.error("I am totally unable to read this gzipped compressed data block, giving up")
    return rawData


def decBzip2(stream):
    """

    Decompress a chunk of data using the bzip2 algorithm from Python

    """
    if bz2 is None:
        raise ImportError("bz2 module is not available")
    return bz2.decompress(stream)


def decZlib(stream):
    """

    Decompress a chunk of data using the zlib algorithm from Python

    """
    if zlib is None:
        raise ImportError("zlib module is not available")
    return zlib.decompress(stream)




def decByteOffset_numpy(stream, size=None):
    """
    Analyze a stream of char with any length of exception:
                2, 4, or 8 bytes integers

    @param stream: string representing the compressed data
    @param size: the size of the output array (of longInts)
    @return: 1D-ndarray

    """
    logger.debug("CBF decompression using Numpy")
    listnpa = []
    key16 = b"\x80"
    key32 = b"\x00\x80"
    key64 = b"\x00\x00\x00\x80"
    shift = 1
    while True:
        idx = stream.find(key16)
        if idx == -1:
            listnpa.append(numpy.fromstring(stream, dtype="int8"))
            break
        listnpa.append(numpy.fromstring(stream[:idx], dtype="int8"))

        if stream[idx + 1:idx + 3] == key32:
            if stream[idx + 3:idx + 7] == key64:
                # 64 bits int
                res = numpy.fromstring(stream[idx + 7:idx + 15], dtype="int64")
                listnpa.append(res)
                shift = 15
            else:
                # 32 bits int
                res = numpy.fromstring(stream[idx + 3:idx + 7], dtype="int32")
                listnpa.append(res)
                shift = 7
        else:  # int16
            res = numpy.fromstring(stream[idx + 1:idx + 3], dtype="int16")
            listnpa.append(res)
            shift = 3
        stream = stream[idx + shift:]
    if not numpy.little_endian:
        for res in listnpa:
            if res.dtype != numpy.int8:
                res.byteswap(True)
    return  (numpy.hstack(listnpa)).astype("int64").cumsum()


def decByteOffset_cython(stream, size=None):
    """
    Analyze a stream of char with any length of exception:
                2, 4, or 8 bytes integers

    @param stream: string representing the compressed data
    @param size: the size of the output array (of longInts)
    @return: 1D-ndarray

    """
    logger.debug("CBF decompression using cython")
    try:
        from .byte_offset import analyseCython
    except ImportError as error:
        logger.error("Failed to import byte_offset cython module, falling back on numpy method")
        return decByteOffset_numpy(stream, size)
    else:
        return analyseCython(stream, size)

decByteOffset = decByteOffset_cython


def compByteOffset_numpy(data):
    """
    Compress a dataset into a string using the byte_offet algorithm

    @param data: ndarray
    @return: string/bytes with compressed data

    test = numpy.array([0,1,2,127,0,1,2,128,0,1,2,32767,0,1,2,32768,0,1,2,2147483647,0,1,2,2147483648,0,1,2,128,129,130,32767,32768,128,129,130,32768,2147483647,2147483648])

    """
    flat = data.astype("int64").ravel()
    delta = numpy.zeros_like(flat)
    delta[0] = flat[0]
    delta[1:] = flat[1:] - flat[:-1]
    mask = ((delta > 127) + (delta < -127))
    exceptions = numpy.nonzero(mask)[0]
    if numpy.little_endian:
        byteswap = False
    else:
        byteswap = True
    start = 0
    binary_blob = b""
    for stop in exceptions:
        if stop - start > 0:
            binary_blob += delta[start:stop].astype("int8").tostring()
        exc = delta[stop]
        if (exc > 2147483647) or (exc < -2147483647):  # 2**31-1
            binary_blob += b"\x80\x00\x80\x00\x00\x00\x80"
            if byteswap:
                binary_blob += delta[stop:stop + 1].byteswap().tostring()
            else:
                binary_blob += delta[stop:stop + 1].tostring()
        elif (exc > 32767) or (exc < -32767):  # 2**15-1
            binary_blob += b"\x80\x00\x80"
            if byteswap:
                binary_blob += delta[stop:stop + 1].astype("int32").byteswap().tostring()
            else:
                binary_blob += delta[stop:stop + 1].astype("int32").tostring()
        else:  # >127
            binary_blob += b"\x80"
            if byteswap:
                binary_blob += delta[stop:stop + 1].astype("int16").byteswap().tostring()
            else:
                binary_blob += delta[stop:stop + 1].astype("int16").tostring()
        start = stop + 1
    if start < delta.size:
        binary_blob += delta[start:].astype("int8").tostring()
    return binary_blob

compByteOffset = compByteOffset_numpy


def decTY1(raw_8, raw_16=None, raw_32=None):
    """
    Modified byte offset decompressor used in Oxford Diffraction images

    Note: Always expect little endian data on the disk

    @param raw_8:  strings containing raw data with integer 8 bits
    @param raw_16: strings containing raw data with integer 16 bits
    @param raw_32: strings containing raw data with integer 32 bits
    @return: numpy.ndarray

    """
    data = numpy.fromstring(raw_8, dtype="uint8").astype(int)
    data -= 127
    if raw_32 is not None:
        int32 = numpy.fromstring(raw_32, dtype="int32")
        if not numpy.little_endian:
            int32.byteswap(True)
        exception32 = numpy.nonzero(data == 128)
    if raw_16 is not None:
        int16 = numpy.fromstring(raw_16, dtype="int16")
        if not numpy.little_endian:
            int16.byteswap(True)
        exception16 = numpy.nonzero(data == 127)
        data[exception16] = int16
    if raw_32:
        data[exception32] = int32
    summed = data.cumsum()
    smax = summed.max()
    if (smax > (2 ** 31 - 1)):
        bytecode = "int64"
    elif (smax > (2 ** 15 - 1)):
        bytecode = "int32"
    elif (smax > (2 ** 7 - 1)):
        bytecode = "int16"
    else:
        bytecode = "int8"
    return summed.astype(bytecode)
decKM4CCD = decTY1

def compTY1(data):
    """
    Modified byte offset compressor used in Oxford Diffraction images

    @param data: numpy.ndarray with the input data (integers!)
    @return: 3-tuple of strings: raw_8,raw_16,raw_32 containing raw data with integer of the given size

    """
    fdata = data.ravel()
    diff = numpy.zeros_like(fdata)
    diff[0] = fdata[0]
    diff[1:] = fdata[1:] - fdata[:-1]
    adiff = abs(diff)
    exception32 = (adiff > (1 << 15) - 1)
    exception16 = (adiff >= (1 << 7) - 1) ^ exception32
    we16 = numpy.where(exception16)
    we32 = numpy.where(exception32)
    data_16 = diff[we16].astype(numpy.int16)
    data_32 = diff[we32].astype(numpy.int32)
    if not numpy.little_endian:
        data_16.byteswap(True)
        data_32.byteswap(True)
    diff[we16] = 127
    diff[we32] = 128
    diff += 127
    data_8 = diff.astype(numpy.uint8)
    return  data_8.tostring(), data_16.tostring(), data_32.tostring()


def decPCK(stream, dim1=None, dim2=None, overflowPix=None, version=None, normal_start=None, swap_needed=None):
    """
    Modified CCP4  pck decompressor used in MAR345 images

    @param raw: input string (bytes in python3)
    @param dim1,dim2: optional parameters size
    @param overflowPix: optional parameters: number of overflowed pixels
    @param version: PCK version 1 or 2
    @param normal_start: position of the normal value section (can be auto-guessed)
    @param swap_needed: set to True when reading data from a foreign endianness (little on big or big on little)
    @return : ndarray of 2D with the right size

    """
    try:
        from .mar345_IO import uncompress_pck
    except ImportError as  error:
        raise RuntimeError("Unable to import mar345_IO to read compressed dataset")
    if "seek" in dir(stream):
        stream.seek(0)
        raw = stream.read()
    else:
        raw = bytes(stream)

    return uncompress_pck(raw, dim1, dim2, overflowPix, version, normal_start, swap_needed)


def compPCK(data):
    """
    Modified CCP4  pck compressor used in MAR345 images

    @param data: numpy.ndarray (square array)
    @return:  compressed stream

    """
    try:
        from .mar345_IO import compress_pck
    except ImportError as error:
        raise RuntimeError("Unable to import mar345_IO to write compressed dataset")
    return compress_pck(data)


