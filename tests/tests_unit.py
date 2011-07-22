#! /opt/local/bin/python
import unittest
from tests import base
from mock import patch, Mock
import shotgun_api3 as api

class TestShotgunInit(unittest.TestCase):
    '''Test case for Shotgun.__init__'''

    def test_http_proxy(self):
        '''test_http_proxy tests setting of http proxy attributes.'''
        server_path = 'http://server_path'
        script_name = 'script_name'
        api_key     = 'api_key'
        proxy_server = 'somedomain.com'
        proxy_port = 3000
        http_proxy  = 'https://%s:%s/somepage.html' % (proxy_server, proxy_port)

        sg = api.Shotgun(server_path, 
                         script_name, 
                         api_key, 
                         http_proxy=http_proxy,
                         connect=False)
        self.assertEquals(sg.config.proxy_server, proxy_server)
        self.assertEquals(sg.config.proxy_port, proxy_port)

    
class TestCreateSummaryRequest(unittest.TestCase):
    '''Test case for _create_summary_request function and parameter
    validation as it exists in Shotgun.summarize.

    Does not require database connection or test data.'''

    def setUp(self):
        server_path = 'http://server_path'
        script_name = 'script_name'
        api_key     = 'api_key'

        self.sg = api.Shotgun(server_path, 
                              script_name, 
                              api_key, 
                              connect=False)


    def test_filter_operator_none(self):
        expected_logical_operator = 'and'
        filter_operator = None
        result = api.shotgun._create_summary_request('',[],None,filter_operator, None) 
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_all(self):
        expected_logical_operator = 'and'
        filter_operator = 'all'
        result = api.shotgun._create_summary_request('',[],None,filter_operator, None) 
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filter_operator_none(self):
        expected_logical_operator = 'or'
        filter_operator = 'or'
        result = api.shotgun._create_summary_request('',[],None,filter_operator, None) 
        actual_logical_operator = result['filters']['logical_operator']
        self.assertEqual(expected_logical_operator, actual_logical_operator)

    def test_filters(self):
        path = 'path'
        relation = 'relation'
        value = 'value'
        expected_condition = {'path':path, 'relation':relation, 'value':value}
        result = api.shotgun._create_summary_request('', [[path, relation, value]], None, None, None) 
        actual_condition = result['filters']['conditions'][0]

    def test_grouping(self):
        result = api.shotgun._create_summary_request('', [], None, None, None) 
        self.assertFalse(result.has_key('grouping'))
        grouping = ['something']
        result = api.shotgun._create_summary_request('', [], None, None, grouping) 
        self.assertEqual(grouping, result['grouping'])

    def test_filters_type(self):
        '''test_filters_type tests that filters parameter is a list'''
        self.assertRaises(ValueError, self.sg.summarize, '', 'not a list', 'bad meta')

    def test_grouping_type(self):
        '''test_grouping_type tests that grouping parameter is a list or None'''
        self.assertRaises(ValueError, self.sg.summarize, '', [], [], grouping='Not a list')


class TestServerCapabilities(unittest.TestCase):
    def test_no_server_version(self):
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, 'host', {})


    def test_bad_version(self):
        '''test_bad_meta tests passing bad meta data type'''
        self.assertRaises(api.ShotgunError, api.shotgun.ServerCapabilities, 'host', {'version':(0,0,0)})

    def test_dev_version(self):
        serverCapabilities = api.shotgun.ServerCapabilities('host', {'version':(3,4,0,'Dev')})
        self.assertEqual(serverCapabilities.version, (3,4,0))
        self.assertTrue(serverCapabilities.is_dev)

        serverCapabilities = api.shotgun.ServerCapabilities('host', {'version':(2,4,0)})
        self.assertEqual(serverCapabilities.version, (2,4,0))
        self.assertFalse(serverCapabilities.is_dev)

class TestClientCapabilities(unittest.TestCase):

    def test_darwin(self):
        self.assert_platform('Darwin', 'mac')

    def test_windows(self):
        self.assert_platform('Windows','windows')
        
    def test_linux(self):
        self.assert_platform('Linux', 'linux')

    @patch('shotgun_api3.shotgun.platform')
    def assert_platform(self, sys_ret_val, expected, mock_platform):
        mock_platform.system.return_value = sys_ret_val
        expected_local_path_field = "local_path_%s" % expected

        client_caps = api.shotgun.ClientCapabilities()
        self.assertEquals(client_caps.platform, expected)
        self.assertEquals(client_caps.local_path_field, expected_local_path_field)

    @patch('shotgun_api3.shotgun.platform')
    def test_no_platform(self, mock_platform):
        mock_platform.system.return_value = "unsupported"
        client_caps = api.shotgun.ClientCapabilities()
        self.assertIsNone(client_caps.platform)
        self.assertIsNone(client_caps.local_path_field)

        
    @patch('shotgun_api3.shotgun.sys')
    def test_py_version(self, mock_sys):
        major = 2
        minor = 7
        micro = 3
        mock_sys.version_info = (major, minor, micro, 'final', 0)
        expected_py_version = "%s.%s" % (major, minor)
        client_caps = api.shotgun.ClientCapabilities()
        self.assertEquals(client_caps.py_version, expected_py_version)
        






        
        

