"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2019, Shotgun Software Inc.

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import sys

from . import httplib2
from . import sgtimezone
from . import six

# mimetypes is broken on Windows only and for Python 2.7.0 to 2.7.9 inclusively.
# We're bundling the version from 2.7.10.
# See bugs :
# http://bugs.python.org/issue9291  <- Fixed in 2.7.7
# http://bugs.python.org/issue21652 <- Fixed in 2.7.8
# http://bugs.python.org/issue22028 <- Fixed in 2.7.10
if (
    sys.platform == "win32" and      # windows
    six.PY2 and                      # python 2
    sys.version_info[1] == 7 and     # minor version 7
    0 <= sys.version_info[2] <= 9    # a release before 2.7.10
):
    # import the bundled mimetypes (2.7.10)
    from .python2 import mimetypes
else:
    import mimetypes

# make these publicly available via the lib submodule
__all__ = [
    httplib2,
    mimetypes,
    sgtimezone,
    six
]
