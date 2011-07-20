"""
Copyright (C) 2008 Benjamin O'Steen

    This file is part of python-fedoracommons.

    python-fedoracommons is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    python-fedoracommons is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with python-fedoracommons.  If not, see <http://www.gnu.org/licenses/>.

    * Shotgun software: removing gae dependency
"""

__license__ = 'GPL http://www.gnu.org/licenses/gpl.txt'
__author__ = "Benjamin O'Steen <bosteen@gmail.com>"
__version__ = '0.1'

#from google.appengine.api import urlfetch

import urlparse
from urllib import urlencode
import base64
from base64 import encodestring

import re
import md5
import calendar
import time
import random
import sha
import hmac

#from mimeTypes import *

#import mimetypes

from cStringIO import StringIO



# For Auth implemnentation: Digest (from httplib2)
# TODO: !Important - add proper code attribution for httplib2 parts
USE_WWW_AUTH_STRICT_PARSING = 0
conn = None
# In regex below:
#    [^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+             matches a "token" as defined by HTTP
#    "(?:[^\0-\x08\x0A-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?"    matches a "quoted-string" as defined by HTTP, when LWS have already been replaced by a single space
# Actually, as an auth-param value can be either a token or a quoted-string, they are combined in a single pattern which matches both:
#    \"?((?<=\")(?:[^\0-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?(?=\")|(?<!\")[^\0-\x08\x0A-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+(?!\"))\"?
WWW_AUTH_STRICT = re.compile(r"^(?:\s*(?:,\s*)?([^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+)\s*=\s*\"?((?<=\")(?:[^\0-\x08\x0A-\x1f\x7f-\xff\\\"]|\\[\0-\x7f])*?(?=\")|(?<!\")[^\0-\x1f\x7f-\xff()<>@,;:\\\"/[\]?={} \t]+(?!\"))\"?)(.*)$")
WWW_AUTH_RELAXED = re.compile(r"^(?:\s*(?:,\s*)?([^ \t\r\n=]+)\s*=\s*\"?((?<=\")(?:[^\\\"]|\\.)*?(?=\")|(?<!\")[^ \t\r\n,]+(?!\"))\"?)(.*)$")
UNQUOTE_PAIRS = re.compile(r'\\(.)')

def _parse_www_authenticate(headers, headername='www-authenticate'):
    """Returns a dictionary of dictionaries, one dict
    per auth_scheme."""
    retval = {}
    if headers.has_key(headername):
        authenticate = headers[headername].strip()
        www_auth = USE_WWW_AUTH_STRICT_PARSING and WWW_AUTH_STRICT or WWW_AUTH_RELAXED
        while authenticate:
            # Break off the scheme at the beginning of the line
            if headername == 'authentication-info':
                (auth_scheme, the_rest) = ('digest', authenticate)                
            else:
                (auth_scheme, the_rest) = authenticate.split(" ", 1)
            # Now loop over all the key value pairs that come after the scheme, 
            # being careful not to roll into the next scheme
            match = www_auth.search(the_rest)
            auth_params = {}
            while match:
                if match and len(match.groups()) == 3:
                    (key, value, the_rest) = match.groups()
                    auth_params[key.lower()] = UNQUOTE_PAIRS.sub(r'\1', value) # '\\'.join([x.replace('\\', '') for x in value.split('\\\\')])
                match = www_auth.search(the_rest)
            retval[auth_scheme.lower()] = auth_params
            authenticate = the_rest.strip()
    return retval

def _cnonce():
    dig = md5.new("%s:%s" % (time.ctime(), ["0123456789"[random.randrange(0, 9)] for i in range(20)])).hexdigest()
    return dig[:16]

def _wsse_username_token(cnonce, iso_now, password):
    return base64.encodestring(sha.new("%s%s%s" % (cnonce, iso_now, password)).digest()).strip()

URI = re.compile(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")

def parse_uri(uri):
    """Parses a URI using the regex given in Appendix B of RFC 3986.

        (scheme, authority, path, query, fragment) = parse_uri(uri)
    """
    groups = URI.match(uri).groups()
    return (groups[1], groups[3], groups[4], groups[6], groups[8])

# For credentials we need two things, first 
# a pool of credential to try (not necesarily tied to BAsic, Digest, etc.)
# Then we also need a list of URIs that have already demanded authentication
# That list is tricky since sub-URIs can take the same auth, or the 
# auth scheme may change as you descend the tree.
# So we also need each Auth instance to be able to tell us
# how close to the 'top' it is.

class Authentication(object):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        self.path = path
        self.host = host
        self.credentials = credentials
        self.http = http

    def depth(self, request_uri):
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        return request_uri[len(self.path):].count("/")

    def inscope(self, host, request_uri):
        # XXX Should we normalize the request_uri?
        (scheme, authority, path, query, fragment) = parse_uri(request_uri)
        return (host == self.host) and path.startswith(self.path)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header. Over-rise this in sub-classes."""
        pass

    def response(self, response, content):
        """Gives us a chance to update with new nonces
        or such returned from the last authorized response.
        Over-rise this in sub-classes if necessary.

        Return TRUE is the request is to be retried, for 
        example Digest may return stale=true.
        """
        return False



class BasicAuthentication(Authentication):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers['authorization'] = 'Basic ' + base64.b64encode("%s:%s" % self.credentials).strip()


class DigestAuthentication(Authentication):
    """Only do qop='auth' and MD5, since that 
    is all Apache currently implements"""
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = _parse_www_authenticate(response, 'www-authenticate')
        self.challenge = challenge['digest']
        qop = self.challenge.get('qop', 'auth')
        self.challenge['qop'] = ('auth' in [x.strip() for x in qop.split()]) and 'auth' or None
        if self.challenge['qop'] is None:
            raise UnimplementedDigestAuthOptionError( _("Unsupported value for qop: %s." % qop))
        self.challenge['algorithm'] = self.challenge.get('algorithm', 'MD5').upper()
        if self.challenge['algorithm'] != 'MD5':
            raise UnimplementedDigestAuthOptionError( _("Unsupported value for algorithm: %s." % self.challenge['algorithm']))
        self.A1 = "".join([self.credentials[0], ":", self.challenge['realm'], ":", self.credentials[1]])   
        self.challenge['nc'] = 1

    def request(self, method, request_uri, headers, content, cnonce = None):
        """Modify the request headers"""
        H = lambda x: md5.new(x).hexdigest()
        KD = lambda s, d: H("%s:%s" % (s, d))
        A2 = "".join([method, ":", request_uri])
        self.challenge['cnonce'] = cnonce or _cnonce() 
        request_digest  = '"%s"' % KD(H(self.A1), "%s:%s:%s:%s:%s" % (self.challenge['nonce'], 
                    '%08x' % self.challenge['nc'], 
                    self.challenge['cnonce'], 
                    self.challenge['qop'], H(A2)
                    )) 
        headers['Authorization'] = 'Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s, response=%s, qop=%s, nc=%08x, cnonce="%s"' % (
                self.credentials[0], 
                self.challenge['realm'],
                self.challenge['nonce'],
                request_uri, 
                self.challenge['algorithm'],
                request_digest,
                self.challenge['qop'],
                self.challenge['nc'],
                self.challenge['cnonce'],
                )
        self.challenge['nc'] += 1

    def response(self, response, content):
        if not response.has_key('authentication-info'):
            challenge = _parse_www_authenticate(response, 'www-authenticate').get('digest', {})
            if 'true' == challenge.get('stale'):
                self.challenge['nonce'] = challenge['nonce']
                self.challenge['nc'] = 1 
                return True
        else:
            updated_challenge = _parse_www_authenticate(response, 'authentication-info').get('digest', {})

            if updated_challenge.has_key('nextnonce'):
                self.challenge['nonce'] = updated_challenge['nextnonce']
                self.challenge['nc'] = 1 
        return False


class HmacDigestAuthentication(Authentication):
    """Adapted from Robert Sayre's code and DigestAuthentication above."""
    __author__ = "Thomas Broyer (t.broyer@ltgt.net)"

    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = _parse_www_authenticate(response, 'www-authenticate')
        self.challenge = challenge['hmacdigest']
        # TODO: self.challenge['domain']
        self.challenge['reason'] = self.challenge.get('reason', 'unauthorized')
        if self.challenge['reason'] not in ['unauthorized', 'integrity']:
            self.challenge['reason'] = 'unauthorized'
        self.challenge['salt'] = self.challenge.get('salt', '')
        if not self.challenge.get('snonce'):
            raise UnimplementedHmacDigestAuthOptionError( _("The challenge doesn't contain a server nonce, or this one is empty."))
        self.challenge['algorithm'] = self.challenge.get('algorithm', 'HMAC-SHA-1')
        if self.challenge['algorithm'] not in ['HMAC-SHA-1', 'HMAC-MD5']:
            raise UnimplementedHmacDigestAuthOptionError( _("Unsupported value for algorithm: %s." % self.challenge['algorithm']))
        self.challenge['pw-algorithm'] = self.challenge.get('pw-algorithm', 'SHA-1')
        if self.challenge['pw-algorithm'] not in ['SHA-1', 'MD5']:
            raise UnimplementedHmacDigestAuthOptionError( _("Unsupported value for pw-algorithm: %s." % self.challenge['pw-algorithm']))
        if self.challenge['algorithm'] == 'HMAC-MD5':
            self.hashmod = md5
        else:
            self.hashmod = sha
        if self.challenge['pw-algorithm'] == 'MD5':
            self.pwhashmod = md5
        else:
            self.pwhashmod = sha
        self.key = "".join([self.credentials[0], ":",
                    self.pwhashmod.new("".join([self.credentials[1], self.challenge['salt']])).hexdigest().lower(),
                    ":", self.challenge['realm']
                    ])
        self.key = self.pwhashmod.new(self.key).hexdigest().lower()

    def request(self, method, request_uri, headers, content):
        """Modify the request headers"""
        keys = _get_end2end_headers(headers)
        keylist = "".join(["%s " % k for k in keys])
        headers_val = "".join([headers[k] for k in keys])
        created = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        cnonce = _cnonce()
        request_digest = "%s:%s:%s:%s:%s" % (method, request_uri, cnonce, self.challenge['snonce'], headers_val)
        request_digest  = hmac.new(self.key, request_digest, self.hashmod).hexdigest().lower()
        headers['Authorization'] = 'HMACDigest username="%s", realm="%s", snonce="%s", cnonce="%s", uri="%s", created="%s", response="%s", headers="%s"' % (
                self.credentials[0], 
                self.challenge['realm'],
                self.challenge['snonce'],
                cnonce,
                request_uri, 
                created,
                request_digest,
                keylist,
                )

    def response(self, response, content):
        challenge = _parse_www_authenticate(response, 'www-authenticate').get('hmacdigest', {})
        if challenge.get('reason') in ['integrity', 'stale']:
            return True
        return False


class WsseAuthentication(Authentication):
    """This is thinly tested and should not be relied upon.
    At this time there isn't any third party server to test against.
    Blogger and TypePad implemented this algorithm at one point
    but Blogger has since switched to Basic over HTTPS and 
    TypePad has implemented it wrong, by never issuing a 401
    challenge but instead requiring your client to telepathically know that
    their endpoint is expecting WSSE profile="UsernameToken"."""
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers['Authorization'] = 'WSSE profile="UsernameToken"'
        iso_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cnonce = _cnonce()
        password_digest = _wsse_username_token(cnonce, iso_now, self.credentials[1])
        headers['X-WSSE'] = 'UsernameToken Username="%s", PasswordDigest="%s", Nonce="%s", Created="%s"' % (
                self.credentials[0],
                password_digest,
                cnonce,
                iso_now)


class GoogleLoginAuthentication(Authentication):
    def __init__(self, credentials, host, request_uri, headers, response, content, http):
        from urllib import urlencode
        Authentication.__init__(self, credentials, host, request_uri, headers, response, content, http)
        challenge = _parse_www_authenticate(response, 'www-authenticate')
        service = challenge['googlelogin'].get('service', 'xapi')
        # Bloggger actually returns the service in the challenge
        # For the rest we guess based on the URI
        if service == 'xapi' and  request_uri.find("calendar") > 0:
            service = "cl"
        # No point in guessing Base or Spreadsheet
        #elif request_uri.find("spreadsheets") > 0:
        #    service = "wise"

        auth = dict(Email=credentials[0], Passwd=credentials[1], service=service, source=headers['user-agent'])
        resp, content = self.http.request("https://www.google.com/accounts/ClientLogin", method="POST", body=urlencode(auth), headers={'Content-Type': 'application/x-www-form-urlencoded'})
        lines = content.split('\n')
        d = dict([tuple(line.split("=", 1)) for line in lines if line])
        if resp.status == 403:
            self.Auth = ""
        else:
            self.Auth = d['Auth']

    def request(self, method, request_uri, headers, content):
        """Modify the request headers to add the appropriate
        Authorization header."""
        headers['authorization'] = 'GoogleLogin Auth=' + self.Auth 


class Credentials(object):
    def __init__(self):
        self.credentials = []

    def add(self, name, password, domain=""):
        self.credentials.append((domain.lower(), name, password))

    def clear(self):
        self.credentials = []

    def iter(self, domain):
        for (cdomain, name, password) in self.credentials:
            if cdomain == "" or domain == cdomain:
                yield (name, password) 

#AUTH_SCHEME_CLASSES = {
#    "basic": BasicAuthentication,
#    "Basic": BasicAuthentication,
#    "wsse": WsseAuthentication,
#    "digest": DigestAuthentication,
#    "Digest": DigestAuthentication,
#    "hmacdigest": HmacDigestAuthentication
#}
#
#AUTH_SCHEME_ORDER = ["hmacdigest", "digest", "Digest", "wsse", "basic", "Basic"]
#
#URLFETCH_METHOD_STRING =   {urlfetch.GET:'GET',
#                            urlfetch.PUT:'PUT',
#                            urlfetch.DELETE:'DELETE',
#                            urlfetch.POST:'POST',
#                            urlfetch.HEAD:'HEAD'
#                            }
#
#
#class GAE_Connection:
#    def __init__(self, base_url, username=None, password=None):
#        self.base_url = base_url
#        m = mimeTypes()
#        self.mimetypes = m.getDictionary()
#        
#        # Name/password
#        self.credentials = Credentials()
#        
#        if username and password:
#            self.add_credentials(username, password, domain="")
#
#        # authorization objects
#        self.authorizations = []
#        
#        self.url = urlparse.urlparse(base_url)
#        
#        (scheme, netloc, path, query, fragment) = urlparse.urlsplit(base_url)
#
#        self.scheme = scheme
#        self.host = netloc
#        self.path = path
#
#    def _auth_from_challenge(self, host, request_uri, headers, response, content):
#        """A generator that creates Authorization objects
#           that can be applied to requests.
#        """
#        challenges = _parse_www_authenticate(response, 'www-authenticate')
#        for cred in self.credentials.iter(host):
#            for scheme in AUTH_SCHEME_ORDER:
#                if challenges.has_key(scheme):
#                    yield AUTH_SCHEME_CLASSES[scheme](cred, host, request_uri, headers, response, content, self)
#
#    def add_credentials(self, name, password, domain=""):
#        """Add a name and password that will be used
#        any time a request requires authentication."""
#        self.credentials.add(name, password, domain)
#
#    def clear_credentials(self):
#        """Remove all the names and passwords
#        that are used for authentication"""
#        self.credentials.clear()
#        self.authorizations = []
#   
#    def request_get(self, resource, args = None, headers={}):
#        return self.request(resource, urlfetch.GET, args, headers=headers)
#        
#    def request_delete(self, resource, args = None, headers={}):
#        return self.request(resource, urlfetch.DELETE, args, headers=headers)
#        
#    def request_post(self, resource, args = None, body = None, filename=None, headers={}):
#        return self.request(resource, urlfetch.POST, args , body = body, filename=filename, headers=headers)
#        
#    def request_put(self, resource, args = None, body = None, filename=None, headers={}):
#        return self.request(resource, urlfetch.PUT, args , body = body, filename=filename, headers=headers)
#        
#    def request_head(self, resource, args = None, body = None, filename=None, headers={}):
#        return self.request(resource, urlfetch.HEAD, args , body = body, filename=filename, headers=headers)
#        
#    def _conn_request(self, conn, request_uri, method, body, headers):
#        # Shim to allow easy reuse of httplib2 auth methods - conn param is not used
#        urlfetch_response = urlfetch.fetch(request_uri, method=method, payload=body, headers=headers)
#        r_headers={'status':urlfetch_response.status_code}
#        for header_key in urlfetch_response.headers:
#            r_headers[header_key.lower()] = urlfetch_response.headers[header_key]
#        
#        return (r_headers, urlfetch_response.content.decode('UTF-8'))
#        
#    def get_content_type(self, filename):
#        extension = filename.split('.')[-1]
#        guessed_mimetype = self.mimetypes.get(extension, mimetypes.guess_type(filename)[0])
#        return guessed_mimetype or 'application/octet-stream'
#        
#    def request(self, resource, method = urlfetch.GET, args = None, body = None, filename=None, headers={}):
#        params = None
#        path = resource
#        headers['User-Agent'] = 'Basic Agent'
#        
#        if not headers.get('Content-Type', None):
#            headers['Content-Type']='text/plain'
#            
#        request_path = []
#        if self.path != "/":
#            if self.path.endswith('/'):
#                request_path.append(self.path[:-1])
#            else:
#                request_path.append(self.path)
#            if path.startswith('/'):
#                request_path.append(path[1:])
#            else:
#                request_path.append(path)
#        full_path = u'/'.join(request_path)
#        
#        if args:
#            full_path += u"?%s" % (urlencode(args))
#            
#        request_uri = u"%s://%s%s" % (self.scheme, self.host, full_path)
#        
#        auths = [(auth.depth(request_uri), auth) for auth in self.authorizations if auth.inscope(host, request_uri)]
#        auth = auths and sorted(auths)[0][1] or None
#        if auth: 
#            auth.request(method, request_uri, headers, body)
#        
#        (response, content) = self._conn_request(conn, request_uri, method, body, headers)
#        
#        if auth: 
#            if auth.response(response, body):
#                auth.request(URLFETCH_METHOD_STRING[method], request_uri, headers, body)
#                
#                (response, content) = self._conn_request(conn, request_uri, method, body, headers)
#
#        if response['status'] == 401:
#            #return {u"body":u"".join(["%s: %s" % (key, response[key]) for key in response])}
#            for authorization in self._auth_from_challenge(self.host, request_uri, headers, response, content):
#                authorization.request(URLFETCH_METHOD_STRING[method], request_uri, headers, body) 
#                
#                (response, content) = self._conn_request(conn, request_uri, method, body, headers)
#                
#                if response['status'] != 401:
#                    self.authorizations.append(authorization)
#                    authorization.response(response, body)
#                    break
#        
#        return {u'headers':response, u'body':content}

