import sys
import os
import logging

from .lib.httplib2 import Http, ProxyInfo, socks
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


import mimetypes    # used for attachment upload
try:
    mimetypes.add_type('video/webm','.webm') # try adding to test for unicode error
except UnicodeDecodeError:
    # Ticket #25579 python bug on windows with unicode
    # Use patched version of mimetypes
    from .lib import mimetypes as mimetypes
