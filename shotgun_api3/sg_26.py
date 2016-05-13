import sys
import os
import logging

from .lib.httplib2 import Http, ProxyInfo, socks, SSLHandshakeError
from .lib.sgtimezone import SgTimezone
from .lib.xmlrpclib import Error, ProtocolError, ResponseError


LOG = logging.getLogger("shotgun_api3")
LOG.setLevel(logging.WARN)

try:
    import simplejson as json
except ImportError:
    LOG.debug("simplejson not found, dropping back to json")
    try:
        import json as json
    except ImportError:
        LOG.debug("json not found, dropping back to embedded simplejson")
        # We need to munge the path so that the absolute imports in simplejson will work.
        dir_path = os.path.dirname(__file__)
        lib_path = os.path.join(dir_path, 'lib')
        sys.path.append(lib_path)
        from .lib import simplejson as json
        sys.path.pop()


def _is_mimetypes_broken():
    """
    Checks if this version of Python ships with a broken version of mimetypes

    :returns: True if the version of mimetypes is broken, False otherwise.
    """
    # mimetypes is broken on Windows only and for Python 2.7.0 to 2.7.9 inclusively.
    # We're bundling the version from 2.7.10.
    # See bugs :
    # http://bugs.python.org/issue9291  <- Fixed in 2.7.7
    # http://bugs.python.org/issue21652 <- Fixed in 2.7.8
    # http://bugs.python.org/issue22028 <- Fixed in 2.7.10
    return (sys.platform == "win32" and
            sys.version_info[0] == 2 and sys.version_info[1] == 7 and
            sys.version_info[2] >= 0 and sys.version_info[2] <= 9)

if _is_mimetypes_broken():
    from .lib import mimetypes as mimetypes
else:
    import mimetypes
