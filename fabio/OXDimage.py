#!/usr/bin/env python
#coding: utf8

"""
Reads Oxford Diffraction Sapphire 3 images

Authors: Henning O. Sorensen & Erik Knudsen
         Center for Fundamental Research: Metal Structures in Four Dimensions
         Risoe National Laboratory
         Frederiksborgvej 399
         DK-4000 Roskilde
         email:erik.knudsen@risoe.dk

        + Jon Wright, ESRF
        + Gaël Goret, ESRF
        + Jérôme Kieffer, ESRF

"""

import numpy, logging
logger = logging.getLogger("OXDimage")
from fabioimage import fabioimage
from compression import decTY1

DETECTOR_TYPES = {0: 'Sapphire/KM4CCD (1x1: 0.06mm, 2x2: 0.12mm)',
1: 'Sapphire2-Kodak (1x1: 0.06mm, 2x2: 0.12mm)',
2: 'Sapphire3-Kodak (1x1: 0.03mm, 2x2: 0.06mm, 4x4: 0.12mm)',
3: 'Onyx-Kodak (1x1: 0.06mm, 2x2: 0.12mm, 4x4: 0.24mm)',
4: 'Unknown Oxford diffraction detector'}


class OXDimage(fabioimage):
    def _readheader(self, infile):

        infile.seek(0)

        # Ascii header part 512 byes long 
        self.header['Header Version'] = infile.readline()[:-2]
        block = infile.readline()
        self.header['Compression'] = block[12:15]
        block = infile.readline()
        self.header['NX'] = int(block[3:7])
        self.header['NY'] = int(block[11:15])
        self.header['OI'] = int(block[19:26])
        self.header['OL'] = int(block[30:37])
        block = infile.readline()
        self.header['Header Size In Bytes'] = int(block[8:15])
        #self.header['NG'] = int(block[19:26])
        #self.header['NK'] = int(block[30:37])
        #self.header['NS'] = int(block[41:48])
        #self.header['NH'] = int(block[52:59])
        block = infile.readline()
        #self.header['NSUPPLEMENT'] = int(block[12:19])
        block = infile.readline()
        self.header['Time'] = block[5:29]

        # Skip to general section (NG) 512 byes long <<<<<<"
        infile.seek(256)
        block = infile.read(512)
        self.header['Binning in x'] = numpy.fromstring(block[0:2], numpy.uint16)[0]
        self.header['Binning in y'] = numpy.fromstring(block[2:4], numpy.uint16)[0]
        self.header['Detector size x'] = numpy.fromstring(block[22:24], numpy.uint16)[0]
        self.header['Detector size y'] = numpy.fromstring(block[24:26], numpy.uint16)[0]
        self.header['Pixels in x'] = numpy.fromstring(block[26:28], numpy.uint16)[0]
        self.header['Pixels in y'] = numpy.fromstring(block[28:30], numpy.uint16)[0]
        self.header['No of pixels'] = numpy.fromstring(block[36:40], numpy.uint32)[0]

        # Speciel section (NS) 768 bytes long
        block = infile.read(768)
        self.header['Gain'] = numpy.fromstring(block[56:64], numpy.float)[0]
        self.header['Overflows flag'] = numpy.fromstring(block[464:466], numpy.int16)[0]
        self.header['Overflow after remeasure flag'] = numpy.fromstring(block[466:468], numpy.int16)[0]
        self.header['Overflow threshold'] = numpy.fromstring(block[472:476], numpy.int32)[0]
        self.header['Exposure time in sec'] = numpy.fromstring(block[480:488], numpy.float)[0]
        self.header['Overflow time in sec'] = numpy.fromstring(block[488:496], numpy.float)[0]
        self.header['Monitor counts of raw image 1'] = numpy.fromstring(block[528:532], numpy.int32)[0]
        self.header['Monitor counts of raw image 2'] = numpy.fromstring(block[532:536], numpy.int32)[0]
        self.header['Monitor counts of overflow raw image 1'] = numpy.fromstring(block[536:540], numpy.int32)[0]
        self.header['Monitor counts of overflow raw image 2'] = numpy.fromstring(block[540:544], numpy.int32)[0]
        self.header['Unwarping'] = numpy.fromstring(block[544:548], numpy.int32)[0]
        self.header['Detector type'] = DETECTOR_TYPES[numpy.fromstring(block[548:552], numpy.int32)[0]]
        self.header['Real pixel size x (mm)'] = numpy.fromstring(block[568:576], numpy.float)[0]
        self.header['Real pixel size y (mm)'] = numpy.fromstring(block[576:584], numpy.float)[0]

        # KM4 goniometer section (NK) 1024 bytes long
        block = infile.read(1024)
        # Spatial correction file
        self.header['Spatial correction file'] = block[26:272]
        self.header['Spatial correction file date'] = block[0:26]
        # Angles are in steps due to stepper motors - conversion factor RAD
        # angle[0] = omega, angle[1] = theta, angle[2] = kappa, angle[3] = phi,   
        start_angles_step = numpy.fromstring(block[284:304], numpy.int32)
        end_angles_step = numpy.fromstring(block[324:344], numpy.int32)
        step2rad = numpy.fromstring(block[368:408], numpy.float)
        # calc angles
        start_angles_deg = start_angles_step * step2rad * 180.0 / numpy.pi

        end_angles_deg = end_angles_step * step2rad * 180.0 / numpy.pi
        self.header['Omega start in deg'] = start_angles_deg[0]
        self.header['Theta start in deg'] = start_angles_deg[1]
        self.header['Kappa start in deg'] = start_angles_deg[2]
        self.header['Phi start in deg'] = start_angles_deg[3]
        self.header['Omega end in deg'] = end_angles_deg[0]
        self.header['Theta end in deg'] = end_angles_deg[1]
        self.header['Kappa end in deg'] = end_angles_deg[2]
        self.header['Phi end in deg'] = end_angles_deg[3]

        zero_correction_soft_step = numpy.fromstring(block[512:532], numpy.int32)
        zero_correction_soft_deg = zero_correction_soft_step * step2rad * 180.0 / numpy.pi
        self.header['Omega zero corr. in deg'] = zero_correction_soft_deg[0]
        self.header['Theta zero corr. in deg'] = zero_correction_soft_deg[1]
        self.header['Kappa zero corr. in deg'] = zero_correction_soft_deg[2]
        self.header['Phi zero corr. in deg'] = zero_correction_soft_deg[3]
        # Beam rotation about e2,e3
        self.header['Beam rot in deg (e2)'] = numpy.fromstring(block[552:560], numpy.float)[0]
        self.header['Beam rot in deg (e3)'] = numpy.fromstring(block[560:568], numpy.float)[0]
        # Wavelenghts alpha1, alpha2, beta
        self.header['Wavelength alpha1'] = numpy.fromstring(block[568:576], numpy.float)[0]
        self.header['Wavelength alpha2'] = numpy.fromstring(block[576:584], numpy.float)[0]
        self.header['Wavelength alpha'] = numpy.fromstring(block[584:592], numpy.float)[0]
        self.header['Wavelength beta'] = numpy.fromstring(block[592:600], numpy.float)[0]

        # Detector tilts around e1,e2,e3 in deg
        self.header['Detector tilt e1 in deg'] = numpy.fromstring(block[640:648], numpy.float)[0]
        self.header['Detector tilt e2 in deg'] = numpy.fromstring(block[648:656], numpy.float)[0]
        self.header['Detector tilt e3 in deg'] = numpy.fromstring(block[656:664], numpy.float)[0]


        # Beam center
        self.header['Beam center x'] = numpy.fromstring(block[664:672], numpy.float)[0]
        self.header['Beam center y'] = numpy.fromstring(block[672:680], numpy.float)[0]
        # Angle (alpha) between kappa rotation axis and e3 (ideally 50 deg)
        self.header['Alpha angle in deg'] = numpy.fromstring(block[672:680], numpy.float)[0]
        # Angle (beta) between phi rotation axis and e3 (ideally 0 deg)
        self.header['Beta angle in deg'] = numpy.fromstring(block[672:680], numpy.float)[0]

        # Detector distance
        self.header['Distance in mm'] = numpy.fromstring(block[712:720], numpy.float)[0]
        # Statistics section (NS) 512 bytes long
        block = infile.read(512)
        self.header['Stat: Min '] = numpy.fromstring(block[0:4], numpy.int32)[0]
        self.header['Stat: Max '] = numpy.fromstring(block[4:8], numpy.int32)[0]
        self.header['Stat: Average '] = numpy.fromstring(block[24:32], numpy.float)[0]
        self.header['Stat: Stddev '] = numpy.sqrt(numpy.fromstring(block[32:40], numpy.float)[0])
        self.header['Stat: Skewness '] = numpy.fromstring(block[40:48], numpy.float)[0]

        # History section (NH) 2048 bytes long - only reads first 256 bytes
        block = infile.read(256)
        self.header['Flood field image'] = block[99:126]

    def read(self, fname, frame=None):
        """
        Read in header into self.header and
            the data   into self.data
        """
        self.header = {}
        self.resetvals()
        infile = self._open(fname)
        self._readheader(infile)

        infile.seek(self.header['Header Size In Bytes'])

        # Compute image size
        try:
            self.dim1 = int(self.header['NX'])
            self.dim2 = int(self.header['NY'])
        except:
            raise Exception("Oxford  file", str(fname) + \
                                "is corrupt, cannot read it")
        #
        if self.header['Compression'] == 'TY1':
            #Compressed with the KM4CCD compression
            raw8 = infile.read(self.dim1 * self.dim2)
            raw16 = None
            raw32 = None
            if self.header['OI'] > 0:
                raw16 = infile.read(self.header['OI'] * 2)
            if self.header['OL'] > 0:
                raw32 = infile.read(self.header['OL'] * 4)

            block = decTY1(raw8, raw16, raw32)
            bytecode = block.dtype

        else:
            bytecode = numpy.int32
            self.bpp = len(numpy.array(0, bytecode).tostring())
            ReadBytes = self.dim1 * self.dim2 * self.bpp
            block = numpy.fromstring(infile.read(ReadBytes), bytecode)

        logger.debug('OVER_SHORT2: %s', block.dtype)
        logger.debug("%s" % (block < 0).sum())
        infile.close()
        logger.debug("BYTECODE: %s", bytecode)
        self.data = block.reshape((self.dim2, self.dim1))
        self.bytecode = self.data.dtype.type
        self.pilimage = None
        return self


