#! /opt/local/bin/python
import sys
import base
import shotgun_api3 as api


class ServerConnectionTest(base.TestBase):
    '''Tests for server connection'''
    def setUp(self):
        super(ServerConnectionTest, self).setUp()

    def test_connection(self):
        '''Tests server connects and returns nothing'''
        result = self.sg.connect()
        self.assertEqual(result, None)

    def test_proxy_info(self):
        '''check proxy value depending http_proxy setting in config'''
        self.sg.connect()
        if self.config.http_proxy:
            sys.stderr.write("[WITH PROXY] ")
            self.assertTrue(isinstance(self.sg._connection.proxy_info, 
                                        api.lib.httplib2.ProxyInfo))
        else:
            sys.stderr.write("[NO PROXY] ")
            self.assertEqual(self.sg._connection.proxy_info, None)







        
        

