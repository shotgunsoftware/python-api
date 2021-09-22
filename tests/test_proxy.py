#! /opt/local/bin/python

# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import sys
from . import base
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
