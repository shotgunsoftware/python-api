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
from . import base
from shotgun_api3.lib import httplib2


class CertificateTest(base.TestBase):
    '''Tests Amazon certificate endpoints'''

    def test_bad_cert_url(self):
        '''Tests that trying to connect to a bad ssl url throws and error'''
        url = "https://untrusted-root.badssl.com/"

        http = httplib2.Http()

        self.assertRaises(
            httplib2.ssl_error_classes, http.request, url
        )

    def test_amazon_cert_urls(self):
        '''Tests we can connect to the Amazon certificate urls endpoints'''
        test_urls = [
            "https://good.sca1a.amazontrust.com/",
            "https://good.sca2a.amazontrust.com/",
            "https://good.sca3a.amazontrust.com/",
            "https://good.sca4a.amazontrust.com/",
            "https://good.sca0a.amazontrust.com/",
        ]

        http = httplib2.Http()

        for url in test_urls:
            response, message = http.request(url)
            assert (response["status"] == "200")
