#!/bin/sh
#
#    Project: Fabio Input/Output
#             https://github.com/kif/fabio
#
#    Copyright (C) 2015 European Synchrotron Radiation Facility, Grenoble, France
#
#    Principal author:       Jérôme Kieffer (Jerome.Kieffer@ESRF.eu)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE

# Script that builds a debian package from this library 

debian=$(grep -o '[0-9]*' /etc/issue)
version=$(cd fabio-src ; python -c"import _version; print(_version.version)"; cd ..)
strictversion=$(cd fabio-src ; python -c"import _version; print(_version.strictversion)"; cd ..) 
tarname=fabio_${strictversion}.orig.tar.gz
if [ -d /usr/lib/ccache ];
then 
   export PATH=/usr/lib/ccache:$PATH 
fi
export PYBUILD_DISABLE_python2=test
export PYBUILD_DISABLE_python3=test
export DEB_BUILD_OPTIONS=nocheck
python setup.py debian_src
cp dist/${tarname} package
cd package
cp ../copyright debian
tar -xzf ${tarname}
newname=python-fabio_${strictversion}.orig.tar.gz
directory=fabio-${strictversion}
ln -s ${tarname} ${newname}
cd ${directory}
cp -r ../debian .
dch -v ${strictversion}-1 "upstream development build of fabio ${version}"
dch --bpo "fabio ${version} built for debian ${debian}"
dpkg-buildpackage -r
cd ..
sudo su -c  "dpkg -i python*.deb fabio*.deb"
#rm -rf ${directory}
cd ..

