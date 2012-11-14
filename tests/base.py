"""Base class for Shotgun API tests."""
import unittest
from ConfigParser import ConfigParser

try:
    import simplejson as json
except ImportError:
    import json

import mock

import shotgun_api3 as api
from shotgun_api3.shotgun import ServerCapabilities

CONFIG_PATH = 'tests/config'

class TestBase(unittest.TestCase):
    '''Base class for tests.

    Sets up mocking and database test data.'''
    def __init__(self, *args, **kws):
        unittest.TestCase.__init__(self, *args, **kws)
        self.human_user     = None
        self.project        = None
        self.shot           = None
        self.asset          = None
        self.version        = None
        self.note           = None
        self.task           = None
        self.ticket         = None
        self.human_password = None
        self.server_url     = None
        self.server_address = None
        self.connect        = False


    def setUp(self):
        self.config = SgTestConfig()
        self.config.read_config(CONFIG_PATH)
        self.human_password = self.config.human_password
        self.server_url     = self.config.server_url
        self.script_name    = self.config.script_name
        self.api_key        = self.config.api_key
        self.http_proxy     = self.config.http_proxy
        self.session_uuid   = self.config.session_uuid


        self.sg = api.Shotgun(self.config.server_url,
                              self.config.script_name,
                              self.config.api_key,
                              http_proxy=self.config.http_proxy,
                              connect=self.connect)

        if self.config.session_uuid:
            self.sg.set_session_uuid(self.config.session_uuid)


    def tearDown(self):
        self.sg = None


class MockTestBase(TestBase):
    '''Test base for tests mocking server interactions.'''
    def setUp(self):
        super(MockTestBase, self).setUp()
        #TODO see if there is another way to stop sg connecting
        self._setup_mock()
        self._setup_mock_data()


    def _setup_mock(self):
        """Setup mocking on the ShotgunClient to stop it calling a live server
        """
        #Replace the function used to make the final call to the server
        #eaiser than mocking the http connection + response
        self.sg._http_request = mock.Mock(spec=api.Shotgun._http_request,
                                          return_value=((200, "OK"), {}, None))

        #also replace the function that is called to get the http connection
        #to avoid calling the server. OK to return a mock as we will not use
        #it
        self.mock_conn = mock.Mock(spec=api.lib.httplib2.Http)
        #The Http objects connection property is a dict of connections
        #it is holding
        self.mock_conn.connections = dict()
        self.sg._connection = self.mock_conn
        self.sg._get_connection = mock.Mock(return_value=self.mock_conn)

        #create the server caps directly to say we have the correct version
        self.sg._server_caps = ServerCapabilities(self.sg.config.server,
                                                  {"version" : [2,4,0]})


    def _mock_http(self, data, headers=None, status=None):
        """Setup a mock response from the SG server.

        Only has an affect if the server has been mocked.
        """
        #test for a mock object rather than config.mock as some tests
        #force the mock to be created
        if not isinstance(self.sg._http_request, mock.Mock):
            return

        if not isinstance(data, basestring):
            data = json.dumps(data, ensure_ascii=False, encoding="utf-8")

        resp_headers = { 'cache-control': 'no-cache',
                         'connection': 'close',
                         'content-length': (data and str(len(data))) or 0 ,
                         'content-type': 'application/json; charset=utf-8',
                         'date': 'Wed, 13 Apr 2011 04:18:58 GMT',
                         'server': 'Apache/2.2.3 (CentOS)',
                         'status': '200 OK' }
        if headers:
            resp_headers.update(headers)

        if not status:
            status = (200, "OK")
        #create a new mock to reset call list etc.
        self._setup_mock()
        self.sg._http_request.return_value = (status, resp_headers, data)


    def _assert_http_method(self, method, params, check_auth=True):
        """Asserts _http_request is called with the method and params."""
        args, _ = self.sg._http_request.call_args
        arg_body = args[2]
        assert isinstance(arg_body, basestring)
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
        self.human_user = { 'id':1,
                            'login':self.config.human_login,
                            'type':'HumanUser' }
        self.project    = { 'id':2,
                            'name':self.config.project_name,
                            'type':'Project' }
        self.shot       = { 'id':3,
                            'code':self.config.shot_code,
                            'type':'Shot' }
        self.asset      = { 'id':4,
                            'code':self.config.asset_code,
                            'type':'Asset' }
        self.version    = { 'id':5,
                            'code':self.config.version_code,
                            'type':'Version' }
        self.ticket    = { 'id':6,
                            'title':self.config.ticket_title,
                            'type':'Ticket' }

class LiveTestBase(TestBase):
    '''Test base for tests relying on connection to server.'''
    def setUp(self):
        super(LiveTestBase, self).setUp()
        self.sg_version = self.sg.info()['version'][:3]
        self._setup_db(self.config)
        if self.sg.server_caps.version and \
           self.sg.server_caps.version >= (3, 3, 0) and \
           (self.sg.server_caps.host.startswith('0.0.0.0') or \
            self.sg.server_caps.host.startswith('127.0.0.1')):
                self.server_address = re.sub('^0.0.0.0|127.0.0.1', 'localhost', self.sg.server_caps.host)
        else:
            self.server_address = self.sg.server_caps.host

    def _setup_db(self, config):
        data = {'name':self.config.project_name}
        self.project = _find_or_create_entity(self.sg, 'Project', data)

        data = {'name':self.config.human_name,
                'login':self.config.human_login,
                'password_proxy':self.config.human_password}
        if self.sg_version >= (3, 0, 0):
            data['locked_until'] = None


        self.human_user = _find_or_create_entity(self.sg, 'HumanUser', data)

        data = {'code':self.config.asset_code,
                'project':self.project}
        keys = ['code']
        self.asset = _find_or_create_entity(self.sg, 'Asset', data, keys)

        data = {'project':self.project,
                'code':self.config.version_code,
                'entity':self.asset,
                'user':self.human_user}
        keys = ['code','project']
        self.version = _find_or_create_entity(self.sg, 'Version', data, keys)

        keys = ['code','project']
        data = {'code':self.config.shot_code,
                'project':self.project}
        self.shot = _find_or_create_entity(self.sg, 'Shot', data, keys)

        keys = ['project','user']
        data = {'project':self.project,
                'user':self.human_user,
                'content':'anything'}
        self.note = _find_or_create_entity(self.sg, 'Note', data, keys)

        keys = ['project', 'entity', 'content']
        data = {'project':self.project,
                'entity':self.asset,
                'content':self.config.task_content,
                'color':'Black',
                'due_date':'1968-10-13',
                'task_assignees': [self.human_user],
                'sg_status_list': 'ip'}
        self.task =  _find_or_create_entity(self.sg, 'Task', data, keys)

        data = {'project':self.project,
                'title':self.config.ticket_title,
                'sg_priority': '3'}
        keys = ['title','project', 'sg_priority']
        self.ticket = _find_or_create_entity(self.sg, 'Ticket', data, keys)

        keys = ['project', 'sg_frames_aspect_ratio', 'frame_count']
        data = {'project':self.project,
                'sg_frames_aspect_ratio': 13.3,
                'frame_count': 33}
        self.version = _find_or_create_entity(self.sg, 'Version', data, keys)

        keys = ['code']
        data = {'code':'api wrapper test storage',
                'mac_path':'nowhere',
                'windows_path':'nowhere',
                'linux_path':'nowhere'}

        self.local_storage = _find_or_create_entity(self.sg, 'LocalStorage', data, keys)


class SgTestConfig(object):
    '''Reads test config and holds values'''
    def __init__(self):
        self.mock           = True
        self.server_url     = None
        self.script_name    = None
        self.api_key        = None
        self.http_proxy     = None
        self.session_uuid   = None
        self.project_name   = None
        self.human_name     = None
        self.human_login    = None
        self.human_password = None
        self.asset_code     = None
        self.version_code   = None
        self.shot_code      = None
        self.task_content   = None


    def read_config(self, config_path):
        config_parser = ConfigParser()
        config_parser.read(config_path)
        for section in config_parser.sections():
            for option in config_parser.options(section):
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
    fields = data.keys()
    filters = [[key, 'is', data[key]] for key in identifyiers]
    entity = sg.find_one(entity_type, filters, fields=fields)
    entity = entity or sg.create(entity_type, data, return_fields=fields)
    assert(entity)
    return entity

