"""Base class for Flow Production Tracking API tests."""
import contextlib
import os
import random
import re
import unittest

from . import mock

import shotgun_api3 as api
from shotgun_api3.shotgun import json
from shotgun_api3.shotgun import ServerCapabilities
from shotgun_api3.lib import six
from shotgun_api3.lib.six.moves import urllib
from shotgun_api3.lib.six.moves.configparser import ConfigParser

try:
    # Attempt to import skip from unittest.  Since this was added in Python 2.7
    # in the case that we're running on Python 2.6 we'll need a decorator to
    # provide some equivalent functionality.
    from unittest import skip
except ImportError:
    # On Python 2.6 we'll just have to ignore tests that are skipped -- we won't
    # mark them as skipped, but we will not fail on them.
    def skip(f):
        return lambda self: None


class TestBase(unittest.TestCase):
    '''Base class for tests.

    Sets up mocking and database test data.'''

    human_user = None
    project = None
    shot = None
    asset = None
    version = None
    note = None
    playlist = None
    task = None
    ticket = None
    human_password = None
    server_url = None
    server_address = None
    session_token = None

    def __init__(self, *args, **kws):
        unittest.TestCase.__init__(self, *args, **kws)
        self.connect = False

    @classmethod
    def setUpClass(cls):
        """
        Loads the configuration file from disk.
        """
        # Since the file is read and never modified, we will only read
        # it once in memory and be done.
        cls.config = SgTestConfig()
        cur_folder = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(cur_folder, "config")
        cls.config.read_config(config_path)

    def setUp(self, auth_mode='ApiUser'):
        # When running the tests from a pull request from a client, the Shotgun
        # site URL won't be set, so do not attempt to run the test.
        if not self.config.server_url:
            self.skipTest("Shotgun site URL is not set. Skipping this test.")

        self.human_login = self.config.human_login
        self.human_password = self.config.human_password
        self.server_url = self.config.server_url
        self.script_name = self.config.script_name
        self.api_key = self.config.api_key
        self.http_proxy = self.config.http_proxy
        self.session_uuid = self.config.session_uuid

        if auth_mode == 'ApiUser':
            self.sg = api.Shotgun(self.config.server_url,
                                  self.config.script_name,
                                  self.config.api_key,
                                  http_proxy=self.config.http_proxy,
                                  connect=self.connect)
        elif auth_mode == 'HumanUser':
            self.sg = api.Shotgun(self.config.server_url,
                                  login=self.human_login,
                                  password=self.human_password,
                                  http_proxy=self.config.http_proxy,
                                  connect=self.connect)
        elif auth_mode == 'SessionToken':
            # first make an instance based on script key/name so
            # we can generate a session token
            sg = api.Shotgun(self.config.server_url,
                             self.config.script_name,
                             self.config.api_key,
                             http_proxy=self.config.http_proxy)
            self.session_token = sg.get_session_token()
            # now log in using session token
            self.sg = api.Shotgun(self.config.server_url,
                                  session_token=self.session_token,
                                  http_proxy=self.config.http_proxy,
                                  connect=self.connect)
        else:
            raise ValueError("Unknown value for auth_mode: %s" % auth_mode)

        if self.config.session_uuid:
            self.sg.set_session_uuid(self.config.session_uuid)

    def tearDown(self):
        self.sg = None


class MockTestBase(TestBase):
    '''Test base for tests mocking server interactions.'''

    def setUp(self):
        super(MockTestBase, self).setUp()
        # TODO see if there is another way to stop sg connecting
        self._setup_mock()
        self._setup_mock_data()

    def _setup_mock(self, s3_status_code_error=503):
        """Setup mocking on the ShotgunClient to stop it calling a live server
        """
        # Replace the function used to make the final call to the server
        # eaiser than mocking the http connection + response
        self.sg._http_request = mock.Mock(spec=api.Shotgun._http_request,
                                          return_value=((200, "OK"), {}, None))
        # Replace the function used to make the final call to the S3 server, and simulate
        # the exception HTTPError raised with 503 status errors
        self.sg._make_upload_request = mock.Mock(spec=api.Shotgun._make_upload_request,
                                                 side_effect = urllib.error.HTTPError(
                                                     "url",
                                                     s3_status_code_error,
                                                     "The server is currently down or to busy to reply."
                                                     "Please try again later.",
                                                     {},
                                                     None
                                                 ))
        # also replace the function that is called to get the http connection
        # to avoid calling the server. OK to return a mock as we will not use
        # it
        self.mock_conn = mock.Mock(spec=api.lib.httplib2.Http)
        # The Http objects connection property is a dict of connections
        # it is holding
        self.mock_conn.connections = dict()
        self.sg._connection = self.mock_conn
        self.sg._get_connection = mock.Mock(return_value=self.mock_conn)

        # create the server caps directly to say we have the correct version
        self.sg._server_caps = ServerCapabilities(self.sg.config.server,
                                                  {"version": [2, 4, 0]})

    def _mock_http(self, data, headers=None, status=None):
        """Setup a mock response from the PTR server.

        Only has an affect if the server has been mocked.
        """
        # test for a mock object rather than config.mock as some tests
        # force the mock to be created
        if not isinstance(self.sg._http_request, mock.Mock):
            return

        if not isinstance(data, six.string_types):
            if six.PY2:
                data = json.dumps(
                    data,
                    ensure_ascii=False,
                    encoding="utf-8"
                )
            else:
                data = json.dumps(
                    data,
                    ensure_ascii=False,
                )

        resp_headers = {'cache-control': 'no-cache',
                        'connection': 'close',
                        'content-length': (data and str(len(data))) or 0,
                        'content-type': 'application/json; charset=utf-8',
                        'date': 'Wed, 13 Apr 2011 04:18:58 GMT',
                        'server': 'Apache/2.2.3 (CentOS)',
                        'status': '200 OK'}
        if headers:
            resp_headers.update(headers)

        if not status:
            status = (200, "OK")
        # create a new mock to reset call list etc.
        self._setup_mock()
        self.sg._http_request.return_value = (status, resp_headers, data)

    def _assert_http_method(self, method, params, check_auth=True):
        """Asserts _http_request is called with the method and params."""
        args, _ = self.sg._http_request.call_args
        arg_body = args[2]
        assert isinstance(arg_body, six.binary_type)
        arg_body = json.loads(arg_body)

        arg_params = arg_body.get("params")

        self.assertEqual(method, arg_body["method_name"])
        if check_auth:
            auth = arg_params[0]
            self.assertEqual(self.script_name, auth["script_name"])
            self.assertEqual(self.api_key, auth["script_key"])

        if params:
            rpc_args = arg_params[len(arg_params)-1]
            self.assertEqual(params, rpc_args)

    def _setup_mock_data(self):
        self.human_user = {'id': 1,
                           'login': self.config.human_login,
                           'type': 'HumanUser'}
        self.project = {'id': 2,
                        'name': self.config.project_name,
                        'type': 'Project'}
        self.shot = {'id': 3,
                     'code': self.config.shot_code,
                     'type': 'Shot'}
        self.asset = {'id': 4,
                      'code': self.config.asset_code,
                      'type': 'Asset'}
        self.version = {'id': 5,
                        'code': self.config.version_code,
                        'type': 'Version'}
        self.ticket = {'id': 6,
                       'title': self.config.ticket_title,
                       'type': 'Ticket'}
        self.playlist = {'id': 7,
                         'code': self.config.playlist_code,
                         'type': 'Playlist'}


class LiveTestBase(TestBase):
    '''Test base for tests relying on connection to server.'''

    def setUp(self, auth_mode='ApiUser'):
        super(LiveTestBase, self).setUp(auth_mode)
        if self.sg.server_caps.version and \
           self.sg.server_caps.version >= (3, 3, 0) and \
           (self.sg.server_caps.host.startswith('0.0.0.0') or
                self.sg.server_caps.host.startswith('127.0.0.1')):
            self.server_address = re.sub('^0.0.0.0|127.0.0.1', 'localhost', self.sg.server_caps.host)
        else:
            self.server_address = self.sg.server_caps.host

    @classmethod
    def setUpClass(cls):
        """
        Sets up common and recurring operations for all tests.
        """
        # The code below simply retrieves entities from Shotgun, or creates
        # them the very first time the test suite is run againt the site.
        # As such, since the operation is read-only, there's no sense
        # reloading stuff from Shotgun over and over again during each test.
        # As such, we are using setUpClass to load them once during the
        # entire duration of the tests.
        super(LiveTestBase, cls).setUpClass()

        # When running the tests from a pull request from a client, the Shotgun
        # site URL won't be set, so do not attempt to connect to Shotgun.
        if cls.config.server_url:
            sg = api.Shotgun(
                cls.config.server_url,
                cls.config.script_name,
                cls.config.api_key
            )
            cls.sg_version = tuple(sg.info()['version'][:3])
            cls._setup_db(cls.config, sg)

    @classmethod
    def _setup_db(cls, config, sg):
        data = {'name': cls.config.project_name}
        cls.project = _find_or_create_entity(sg, 'Project', data)

        data = {'name': cls.config.human_name,
                'login': cls.config.human_login,
                'password_proxy': cls.config.human_password}
        if cls.sg_version >= (3, 0, 0):
            data['locked_until'] = None

        cls.human_user = _find_or_create_entity(sg, 'HumanUser', data)

        data = {'code': cls.config.asset_code,
                'project': cls.project}
        keys = ['code']
        cls.asset = _find_or_create_entity(sg, 'Asset', data, keys)

        data = {'project': cls.project,
                'code': cls.config.version_code,
                'entity': cls.asset,
                'user': cls.human_user,
                'sg_frames_aspect_ratio': 13.3,
                'frame_count': 33}
        keys = ['code', 'project']
        cls.version = _find_or_create_entity(sg, 'Version', data, keys)

        keys = ['code', 'project']
        data = {'code': cls.config.shot_code,
                'project': cls.project}
        cls.shot = _find_or_create_entity(sg, 'Shot', data, keys)

        keys = ['project', 'user']
        data = {'project': cls.project,
                'user': cls.human_user,
                'content': 'anything'}
        cls.note = _find_or_create_entity(sg, 'Note', data, keys)

        keys = ['code', 'project']
        data = {'project': cls.project,
                'code': cls.config.playlist_code}
        cls.playlist = _find_or_create_entity(sg, 'Playlist', data, keys)

        keys = ['code', 'entity_type']
        data = {'code': 'wrapper test step',
                'entity_type': 'Shot'}
        cls.step = _find_or_create_entity(sg, 'Step', data, keys)

        keys = ['project', 'entity', 'content']
        data = {'project': cls.project,
                'entity': cls.asset,
                'content': cls.config.task_content,
                'color': 'Black',
                'due_date': '1968-10-13',
                'task_assignees': [cls.human_user],
                'sg_status_list': 'ip'}
        cls.task = _find_or_create_entity(sg, 'Task', data, keys)

        data = {'project': cls.project,
                'title': cls.config.ticket_title,
                'sg_priority': '3'}
        keys = ['title', 'project', 'sg_priority']
        cls.ticket = _find_or_create_entity(sg, 'Ticket', data, keys)

        keys = ['code']
        data = {'code': 'api wrapper test storage',
                'mac_path': 'nowhere',
                'windows_path': 'nowhere',
                'linux_path': 'nowhere'}
        cls.local_storage = _find_or_create_entity(sg, 'LocalStorage', data, keys)

    @contextlib.contextmanager
    def gen_entity(self, entity_type, **kwargs):
        # Helper creator
        if entity_type == "HumanUser":
            if "login" not in kwargs:
                kwargs["login"] = "test-python-api-{rnd}"

            if "sg_status_list" not in kwargs:
                kwargs["sg_status_list"] = "dis"

            if "password_proxy" not in kwargs:
                kwargs["password_proxy"] = self.config.human_password

        item_rnd = random.randrange(100,999)
        for k in kwargs:
            if isinstance(kwargs[k], str):
                kwargs[k] = kwargs[k].format(rnd=item_rnd)

        entity = self.sg.create(entity_type, kwargs, return_fields=list(kwargs.keys()))
        try:
            yield entity
        finally:
            rv = self.sg.delete(entity_type, entity["id"])
            assert rv == True


class HumanUserAuthLiveTestBase(LiveTestBase):
    '''
    Test base for relying on a Shotgun connection authenticate through the
    configured login/password pair.
    '''

    def setUp(self):
        super(HumanUserAuthLiveTestBase, self).setUp('HumanUser')


class SessionTokenAuthLiveTestBase(LiveTestBase):
    '''
    Test base for relying on a Shotgun connection authenticate through the
    configured session_token parameter.
    '''

    def setUp(self):
        super(SessionTokenAuthLiveTestBase, self).setUp('SessionToken')


class SgTestConfig(object):
    '''Reads test config and holds values'''

    def __init__(self):
        for key in self.config_keys():
            # Look for any environment variables that match our test
            # configuration naming of "SG_{KEY}". Default is None.
            value = os.environ.get('SG_%s' % (str(key).upper()))
            if key in ['mock']:
                value = (value is None) or (str(value).lower() in ['true', '1'])
            setattr(self, key, value)

    def config_keys(self):
        return [
            'api_key', 'asset_code', 'http_proxy', 'human_login', 'human_name',
            'human_password', 'mock', 'project_name', 'script_name',
            'server_url', 'session_uuid', 'shot_code', 'task_content',
            'version_code', 'playlist_code', 'ticket_title'
        ]

    def read_config(self, config_path):
        config_parser = ConfigParser()
        config_parser.read(config_path)
        for section in config_parser.sections():
            for option in config_parser.options(section):
                # We only care about the configuration file if an environment
                # variable has not already been set
                if not getattr(self, option, None):
                    value = config_parser.get(section, option)
                    setattr(self, option, value)


def _find_or_create_entity(sg, entity_type, data, identifyiers=None):
    '''Finds or creates entities.
    @params:
        sg           - shogun_json.Shotgun instance
        entity_type  - entity type
        data         - dictionary of data for the entity
        identifyiers -list of subset of keys from data which should be used to
                      uniquely identity the entity
    @returns dicitonary of the entity values
    '''
    identifyiers = identifyiers or ['name']
    fields = list(data.keys())
    filters = [[key, 'is', data[key]] for key in identifyiers]
    entity = sg.find_one(entity_type, filters, fields=fields)
    entity = entity or sg.create(entity_type, data, return_fields=fields)
    assert(entity)
    return entity
