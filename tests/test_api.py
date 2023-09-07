# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""Test calling the Shotgun API functions.

Includes short run tests, like simple crud and single finds. See
test_api_long for other tests.
"""

from __future__ import print_function
import datetime
import sys
import os
from .mock import patch, MagicMock
import time
import types
import uuid
import unittest
from shotgun_api3.lib.six.moves import range, urllib
import warnings
import glob

import shotgun_api3
from shotgun_api3.lib.httplib2 import Http
from shotgun_api3.lib import six

# To mock the correct exception when testion on Python 2 and 3, use the
# ShotgunSSLError variable from sgsix that contains the appropriate exception
# class for the current Python version.
from shotgun_api3.lib.sgsix import ShotgunSSLError

from . import base

THUMBNAIL_MAX_ATTEMPTS = 30
THUMBNAIL_RETRY_INTERAL = 10
TRANSIENT_IMAGE_PATH = "images/status/transient"


class TestHumanUserAuth(base.HumanUserAuthLiveTestBase):
    """
    Testing the username/password authentication method
    """


    def test_humanuser_upload_thumbnail_for_version(self):
        """simple upload thumbnail for version test as human user."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Version", self.version['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        version_with_thumbnail = find_one_await_thumbnail(self.sg, 'Version', [['id', 'is', self.version['id']]])

        self.assertEqual(version_with_thumbnail.get('type'), 'Version')
        self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])

        h = Http(".cache")
        thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version", self.version['id'], {'image': None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)


class TestSessionTokenAuth(base.SessionTokenAuthLiveTestBase):
    """
    Testing the session token based authentication method
    """

    def test_humanuser_upload_thumbnail_for_version(self):
        """simple upload thumbnail for version test as session based token user."""

        if self.sg.server_caps.version >= (5, 4, 1):

            this_dir, _ = os.path.split(__file__)
            path = os.path.abspath(os.path.expanduser(
                os.path.join(this_dir, "sg_logo.jpg")))

            # upload thumbnail
            thumb_id = self.sg.upload_thumbnail("Version", self.version['id'], path)
            self.assertTrue(isinstance(thumb_id, int))

            # check result on version
            version_with_thumbnail = find_one_await_thumbnail(self.sg, 'Version', [['id', 'is', self.version['id']]])

            self.assertEqual(version_with_thumbnail.get('type'), 'Version')
            self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])

            h = Http(".cache")
            thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
            self.assertEqual(thumb_resp['status'], '200')
            self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

            # clear thumbnail
            response_clear_thumbnail = self.sg.update("Version", self.version['id'], {'image': None})
            expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
            self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)





def _has_unicode(data):
    for k, v in data.items():
        if isinstance(k, six.text_type):
            return True
        if isinstance(v, six.text_type):
            return True
    return False


def _get_path(url):
    """Returns path component of a url without the sheme, host, query, anchor, or any other
    additional elements.
    For example, the url "https://foo.shotgunstudio.com/page/2128#Shot_1190_sr10101_034"
    returns "/page/2128"
    """
    # url_parse returns native objects for older python versions (2.4)
    if isinstance(url, dict):
        return url.get('path')
    elif isinstance(url, tuple):
        # 3rd component is the path
        return url[2]
    else:
        return url.path


def find_one_await_thumbnail(sg, entity_type, filters, fields=["image"], thumbnail_field_name="image", **kwargs):
    attempts = 0
    result = sg.find_one(entity_type, filters, fields=fields, **kwargs)
    while attempts < THUMBNAIL_MAX_ATTEMPTS and TRANSIENT_IMAGE_PATH in result.get(thumbnail_field_name):
        time.sleep(THUMBNAIL_RETRY_INTERAL)
        result = sg.find_one(entity_type, filters, fields=fields, **kwargs)
        attempts += 1
    return result


if __name__ == '__main__':
    unittest.main()
