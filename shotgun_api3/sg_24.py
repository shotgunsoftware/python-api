import os
import sys
import logging

from shotgun_api3.lib.httplib2 import Http, ProxyInfo, socks, SSLHandshakeError
from shotgun_api3.lib.sgtimezone import SgTimezone
from shotgun_api3.lib.xmlrpclib import Error, ProtocolError, ResponseError
import mimetypes    # used for attachment upload


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
        import shotgun_api3.lib.simplejson as json
        sys.path.pop()
