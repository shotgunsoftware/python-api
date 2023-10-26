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


class TestShotgunApi(base.LiveTestBase):
    def setUp(self):
        super(TestShotgunApi, self).setUp()
        # give note unicode content
        self.sg.update('Note', self.note['id'], {'content': u'La Pe\xf1a'})

    def test_info(self):
        """Called info"""
        # TODO do more to check results
        self.sg.info()

    def test_server_dates(self):
        """Pass datetimes to the server"""
        # TODO check results
        t = {'project': self.project,
             'start_date': datetime.date.today()}
        self.sg.create('Task', t, ['content', 'sg_status_list'])

    def test_batch(self):
        """Batched create, update, delete"""

        requests = [
            {
                "request_type": "create",
                "entity_type": "Shot",
                "data": {
                    "code": "New Shot 5",
                    "project": self.project
                }
            },
            {
                "request_type": "update",
                "entity_type": "Shot",
                "entity_id": self.shot['id'],
                "data": {
                    "code": "Changed 1"
                }
            }
        ]

        new_shot, updated_shot = self.sg.batch(requests)

        self.assertEqual(self.shot['id'], updated_shot["id"])
        self.assertTrue(new_shot.get("id"))

        new_shot_id = new_shot["id"]
        requests = [
            {
                "request_type": "delete",
                "entity_type": "Shot",
                "entity_id": new_shot_id
            },
            {
                "request_type": "update",
                "entity_type": "Shot",
                "entity_id": self.shot['id'],
                "data": {"code": self.shot['code']}
            }
        ]

        result = self.sg.batch(requests)[0]
        self.assertEqual(True, result)

    def test_empty_batch(self):
        """Empty list sent to .batch()"""
        result = self.sg.batch([])
        self.assertEqual([], result)

    def test_create_update_delete(self):
        """Called create, update, delete, revive"""
        data = {
            'project': self.project,
            'code': 'JohnnyApple_Design01_FaceFinal',
            'description': 'fixed rig per director final notes',
            'sg_status_list': 'rev',
            'entity': self.asset,
            'user': self.human_user
        }

        version = self.sg.create("Version", data, return_fields=["id"])
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        # TODO check results more thoroughly
        # TODO: test returned fields are requested fields

        data = data = {
            "description": "updated test"
        }
        version = self.sg.update("Version", version["id"], data)
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)

        rv = self.sg.delete("Version", version["id"])
        self.assertEqual(True, rv)
        rv = self.sg.delete("Version", version["id"])
        self.assertEqual(False, rv)

        rv = self.sg.revive("Version", version["id"])
        self.assertEqual(True, rv)
        rv = self.sg.revive("Version", version["id"])
        self.assertEqual(False, rv)

    def test_last_accessed(self):
        page = self.sg.find('Page', [], fields=['last_accessed'], limit=1)
        self.assertEqual("Page", page[0]['type'])
        self.assertEqual(datetime.datetime, type(page[0]['last_accessed']))

    def test_get_session_token(self):
        """Got session UUID"""
        # TODO test results
        rv = self.sg.get_session_token()
        self.assertTrue(rv)

    def test_upload_download(self):
        """Upload and download an attachment tests"""
        # upload / download only works against a live server because it does
        # not use the standard http interface
        if 'localhost' in self.server_url:
            print("upload / down tests skipped for localhost")
            return

        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))
        size = os.stat(path).st_size

        attach_id = self.sg.upload("Ticket",
                                   self.ticket['id'], path, 'attachments',
                                   tag_list="monkeys, everywhere, send, help")

        # test download with attachment_id
        attach_file = self.sg.download_attachment(attach_id)
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        orig_file = open(path, "rb").read()
        self.assertEqual(orig_file, attach_file)

        # test download with attachment_id as keyword
        attach_file = self.sg.download_attachment(attachment_id=attach_id)
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        orig_file = open(path, "rb").read()
        self.assertEqual(orig_file, attach_file)

        # test download with attachment_id (write to disk)
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sg_logo_download.jpg")
        result = self.sg.download_attachment(attach_id, file_path=file_path)
        self.assertEqual(result, file_path)
        # On windows read may not read to end of file unless opened 'rb'
        fp = open(file_path, 'rb')
        attach_file = fp.read()
        fp.close()
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test download with attachment hash
        ticket = self.sg.find_one('Ticket', [['id', 'is', self.ticket['id']]],
                                  ['attachments'])

        # Look for the attachment we just uploaded, the attachments are not returned from latest
        # to earliest.
        attachment = [x for x in ticket["attachments"] if x["id"] == attach_id]
        self.assertEqual(len(attachment), 1)

        attachment = attachment[0]
        attach_file = self.sg.download_attachment(attachment)

        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test download with attachment hash (write to disk)
        result = self.sg.download_attachment(attachment,
                                             file_path=file_path)
        self.assertEqual(result, file_path)
        fp = open(file_path, 'rb')
        attach_file = fp.read()
        fp.close()
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test invalid requests
        INVALID_S3_URL = "https://sg-media-usor-01.s3.amazonaws.com/ada3de3ee3873875e1dd44f2eb0882c75ae36a4a/cd31346421dbeef781e0e480f259a3d36652d7f2/IMG_0465.MOV?AWSAccessKeyId=AKIAIQGOBSVN3FSQ5QFA&Expires=1371789959&Signature=SLbzv7DuVlZ8XAoOSQQAiGpF3u8%3D"  # noqa
        self.assertRaises(shotgun_api3.ShotgunFileDownloadError,
                          self.sg.download_attachment,
                          {"url": INVALID_S3_URL})
        INVALID_ATTACHMENT_ID = 99999999
        self.assertRaises(shotgun_api3.ShotgunFileDownloadError,
                          self.sg.download_attachment,
                          INVALID_ATTACHMENT_ID)
        self.assertRaises(TypeError, self.sg.download_attachment,
                          "/path/to/some/file.jpg")
        self.assertRaises(ValueError, self.sg.download_attachment,
                          {"id": 123, "type": "Shot"})
        self.assertRaises(TypeError, self.sg.download_attachment)

        # test upload of non-ascii, unicode path
        u_path = os.path.abspath(
            os.path.expanduser(
                glob.glob(os.path.join(six.text_type(this_dir), u'No*l.jpg'))[0]
            )
        )

        # If this is a problem, it'll raise with a UnicodeEncodeError. We
        # don't need to check the results of the upload itself -- we're
        # only checking that the non-ascii string encoding doesn't trip
        # us up the way it used to.
        self.sg.upload(
            "Ticket",
            self.ticket['id'],
            u_path,
            'attachments',
            tag_list="monkeys, everywhere, send, help"
        )

        # Also make sure that we can pass in a utf-8 encoded string path
        # with non-ascii characters and have it work properly. This is
        # primarily a concern on Windows, as it doesn't handle that
        # situation as well as OS X and Linux.
        self.sg.upload(
            "Ticket",
            self.ticket['id'],
            u_path.encode("utf-8"),
            'attachments',
            tag_list="monkeys, everywhere, send, help"
        )
        if six.PY2:
            # In Python2, make sure that non-utf-8 encoded paths raise when they
            # can't be converted to utf-8.  For Python3, we'll skip these tests
            # since string encoding is handled differently.

            # We need to touch the file we're going to test with first. We can't
            # bundle a file with this filename in the repo due to some pip install
            # problems on Windows. Note that the path below is utf-8 encoding of
            # what we'll eventually encode as shift-jis.
            file_path_s = os.path.join(this_dir, "./\xe3\x81\x94.shift-jis")
            file_path_u = file_path_s.decode("utf-8")

            with open(file_path_u if sys.platform.startswith("win") else file_path_s, "w") as fh:
                fh.write("This is just a test file with some random data in it.")

            self.assertRaises(
                shotgun_api3.ShotgunError,
                self.sg.upload,
                "Ticket",
                self.ticket['id'],
                file_path_u.encode("shift-jis"),
                'attachments',
                tag_list="monkeys, everywhere, send, help"
            )

            # But it should work in all cases if a unicode string is used.
            self.sg.upload(
                "Ticket",
                self.ticket['id'],
                file_path_u,
                'attachments',
                tag_list="monkeys, everywhere, send, help"
            )

            # cleanup
            os.remove(file_path_u)

        # cleanup
        os.remove(file_path)

    def test_upload_thumbnail_in_create(self):
        """Upload a thumbnail via the create method"""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        # test thumbnail upload
        data = {'image': path, 'code': 'Test Version',
                'project': self.project}
        new_version = self.sg.create("Version", data, return_fields=['image'])
        new_version = find_one_await_thumbnail(
            self.sg,
            "Version",
            [["id", "is", new_version["id"]]],
            fields=["image", "project", "type", "id"]
        )

        self.assertTrue(new_version is not None)
        self.assertTrue(isinstance(new_version, dict))
        self.assertTrue(isinstance(new_version.get('id'), int))
        self.assertEqual(new_version.get('type'), 'Version')
        self.assertEqual(new_version.get('project'), self.project)
        self.assertTrue(new_version.get('image') is not None)

        h = Http(".cache")
        thumb_resp, content = h.request(new_version.get('image'), "GET")
        self.assertIn(thumb_resp['status'], ['200', '304'])
        self.assertIn(thumb_resp['content-type'], ['image/jpeg', 'image/png'])

        self.sg.delete("Version", new_version['id'])

        # test filmstrip image upload
        data = {'filmstrip_image': path, 'code': 'Test Version',
                'project': self.project}
        new_version = self.sg.create("Version", data, return_fields=['filmstrip_image'])
        self.assertTrue(new_version is not None)
        self.assertTrue(isinstance(new_version, dict))
        self.assertTrue(isinstance(new_version.get('id'), int))
        self.assertEqual(new_version.get('type'), 'Version')
        self.assertEqual(new_version.get('project'), self.project)
        self.assertTrue(new_version.get('filmstrip_image') is not None)

        url = new_version.get('filmstrip_image')
        data = self.sg.download_attachment({'url': url})
        self.assertTrue(isinstance(data, six.binary_type))

        self.sg.delete("Version", new_version['id'])
    # end test_upload_thumbnail_in_create

    def test_upload_thumbnail_for_version(self):
        """simple upload thumbnail for version test."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Version", self.version['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        version_with_thumbnail = self.sg.find_one('Version', [['id', 'is', self.version['id']]])
        version_with_thumbnail = find_one_await_thumbnail(self.sg, 'Version', [['id', 'is', self.version['id']]])

        self.assertEqual(version_with_thumbnail.get('type'), 'Version')
        self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])

        h = Http(".cache")
        thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
        self.assertIn(thumb_resp['status'], ['200', '304'])
        self.assertIn(thumb_resp['content-type'], ['image/jpeg', 'image/png'])

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version", self.version['id'], {'image': None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_upload_thumbnail_for_task(self):
        """simple upload thumbnail for task test."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Task", self.task['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        task_with_thumbnail = self.sg.find_one('Task', [['id', 'is', self.task['id']]])
        task_with_thumbnail = find_one_await_thumbnail(self.sg, 'Task', [['id', 'is', self.task['id']]])

        self.assertEqual(task_with_thumbnail.get('type'), 'Task')
        self.assertEqual(task_with_thumbnail.get('id'), self.task['id'])

        h = Http(".cache")
        thumb_resp, content = h.request(task_with_thumbnail.get('image'), "GET")
        self.assertIn(thumb_resp['status'], ['200', '304'])
        self.assertIn(thumb_resp['content-type'], ['image/jpeg', 'image/png'])

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version", self.version['id'], {'image': None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_upload_thumbnail_with_upload_function(self):
        """Upload thumbnail via upload function test"""
        path = os.path.abspath(os.path.expanduser(os.path.join(os.path.dirname(__file__), "sg_logo.jpg")))

        # upload thumbnail
        thumb_id = self.sg.upload("Task", self.task['id'], path, 'image')
        self.assertTrue(isinstance(thumb_id, int))

        # upload filmstrip thumbnail
        f_thumb_id = self.sg.upload("Task", self.task['id'], path, 'filmstrip_image')
        self.assertTrue(isinstance(f_thumb_id, int))

    def test_requires_direct_s3_upload(self):
        """Test _requires_direct_s3_upload"""

        upload_types = self.sg.server_info.get("s3_enabled_upload_types")
        direct_uploads_enabled = self.sg.server_info.get("s3_direct_uploads_enabled")

        self.sg.server_info["s3_enabled_upload_types"] = None
        self.sg.server_info["s3_direct_uploads_enabled"] = None

        # Test s3_enabled_upload_types and s3_direct_uploads_enabled not set
        self.assertFalse(self.sg._requires_direct_s3_upload("Version", "sg_uploaded_movie"))

        self.sg.server_info["s3_enabled_upload_types"] = {
            "Version": ["sg_uploaded_movie"]
        }

        # Test direct_uploads_enabled not set
        self.assertFalse(self.sg._requires_direct_s3_upload("Version", "sg_uploaded_movie"))

        self.sg.server_info["s3_direct_uploads_enabled"] = True

        # Test regular path
        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "sg_uploaded_movie"))
        self.assertFalse(self.sg._requires_direct_s3_upload("Version", "abc"))
        self.assertFalse(self.sg._requires_direct_s3_upload("Abc", "abc"))

        # Test star field wildcard and arrays of fields
        self.sg.server_info["s3_enabled_upload_types"] = {
            "Version": ["sg_uploaded_movie", "test", "other"],
            "Test": ["*"],
            "Asset": "*"
        }

        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "sg_uploaded_movie"))
        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "test"))
        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "other"))
        self.assertTrue(self.sg._requires_direct_s3_upload("Test", "abc"))
        self.assertTrue(self.sg._requires_direct_s3_upload("Asset", "test"))

        # Test default allowed upload type
        self.sg.server_info["s3_enabled_upload_types"] = None
        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "sg_uploaded_movie"))
        self.assertFalse(self.sg._requires_direct_s3_upload("Version", "test"))

        # Test star entity_type
        self.sg.server_info["s3_enabled_upload_types"] = {
            "*": ["sg_uploaded_movie", "test"]
        }
        self.assertTrue(self.sg._requires_direct_s3_upload("Something", "sg_uploaded_movie"))
        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "test"))
        self.assertFalse(self.sg._requires_direct_s3_upload("Version", "other"))

        # Test entity_type and field_name wildcard
        self.sg.server_info["s3_enabled_upload_types"] = {
            "*": "*"
        }
        self.assertTrue(self.sg._requires_direct_s3_upload("Something", "sg_uploaded_movie"))
        self.assertTrue(self.sg._requires_direct_s3_upload("Version", "abc"))

        self.sg.server_info["s3_enabled_upload_types"] = upload_types
        self.sg.server_info["s3_direct_uploads_enabled"] = direct_uploads_enabled

    def test_linked_thumbnail_url(self):
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        thumb_id = self.sg.upload_thumbnail("Project", self.version['project']['id'], path)

        response_version_with_project = find_one_await_thumbnail(
            self.sg,
            "Version",
            [["id", "is", self.version["id"]]],
            fields=["id", "code", "project.Project.image"],
            thumbnail_field_name="project.Project.image"
        )

        if self.sg.server_caps.version and self.sg.server_caps.version >= (3, 3, 0):

            self.assertEqual(response_version_with_project.get('type'), 'Version')
            self.assertEqual(response_version_with_project.get('id'), self.version['id'])
            self.assertEqual(response_version_with_project.get('code'), self.config.version_code)

            h = Http(".cache")
            thumb_resp, content = h.request(response_version_with_project.get('project.Project.image'), "GET")
            self.assertIn(thumb_resp['status'], ['200', '304'])
            self.assertIn(thumb_resp['content-type'], ['image/jpeg', 'image/png'])

        else:
            expected_version_with_project = {
                'code': self.config.version_code,
                'type': 'Version',
                'id': self.version['id'],
                'project.Project.image': thumb_id
            }
            self.assertEqual(expected_version_with_project, response_version_with_project)

    # For now skip tests that are erroneously failling on some sites to
    # allow CI to pass until the known issue causing this is resolved.
    @base.skip("Skipping test that erroneously fails on some sites.")
    def test_share_thumbnail(self):
        """share thumbnail between two entities"""

        def share_thumbnail_retry(*args, **kwargs):
            # Since share_thumbnail raises a ShotgunError if the thumbnail is still
            # pending, sleep and retry if this exception is raised, to allow time for
            # the thumbnail to finish processing.
            thumbnail_id = None
            attempts = 0
            while attempts < THUMBNAIL_MAX_ATTEMPTS and thumbnail_id is None:
                try:
                    thumbnail_id = self.sg.share_thumbnail(*args, **kwargs)
                    attempts += 1
                except shotgun_api3.ShotgunError:
                    time.sleep(THUMBNAIL_RETRY_INTERAL)
            return thumbnail_id

        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(os.path.join(this_dir, "sg_logo.jpg")))

        # upload thumbnail to first entity and share it with the rest
        share_thumbnail_retry([self.version, self.shot], thumbnail_path=path)
        response_version_thumbnail = find_one_await_thumbnail(
            self.sg,
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'image']
        )
        response_shot_thumbnail = find_one_await_thumbnail(
            self.sg,
            'Shot',
            [['id', 'is', self.shot['id']]],
            fields=['id', 'code', 'image']
        )

        shot_url = urllib.parse.urlparse(response_shot_thumbnail.get('image'))
        version_url = urllib.parse.urlparse(response_version_thumbnail.get('image'))
        shot_path = _get_path(shot_url)
        version_path = _get_path(version_url)
        self.assertEqual(shot_path, version_path)

        # share thumbnail from source entity with entities
        self.sg.upload_thumbnail("Version", self.version['id'], path)
        share_thumbnail_retry([self.asset, self.shot], source_entity=self.version)
        response_version_thumbnail = find_one_await_thumbnail(
            self.sg,
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'image']
        )
        response_shot_thumbnail = find_one_await_thumbnail(
            self.sg,
            'Shot',
            [['id', 'is', self.shot['id']]],
            fields=['id', 'code', 'image']
        )
        response_asset_thumbnail = find_one_await_thumbnail(
            self.sg,
            'Asset',
            [['id', 'is', self.asset['id']]],
            fields=['id', 'code', 'image']
        )

        shot_url = urllib.parse.urlparse(response_shot_thumbnail.get('image'))
        version_url = urllib.parse.urlparse(response_version_thumbnail.get('image'))
        asset_url = urllib.parse.urlparse(response_asset_thumbnail.get('image'))

        shot_path = _get_path(shot_url)
        version_path = _get_path(version_url)
        asset_path = _get_path(asset_url)

        self.assertEqual(version_path, shot_path)
        self.assertEqual(version_path, asset_path)

        # raise errors when missing required params or providing conflicting ones
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.share_thumbnail,
                          [self.shot, self.asset], path, self.version)
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.share_thumbnail,
                          [self.shot, self.asset])

    @patch('shotgun_api3.Shotgun._send_form')
    def test_share_thumbnail_not_ready(self, mock_send_form):
        """throw an exception if trying to share a transient thumbnail"""

        mock_send_form.method.assert_called_once()
        mock_send_form.return_value = ("2"
                                       "\nsource_entity image is a transient thumbnail that cannot be shared. "
                                       "Try again later, when the final thumbnail is available\n")

        self.assertRaises(shotgun_api3.ShotgunThumbnailNotReady, self.sg.share_thumbnail,
                          [self.version, self.shot], source_entity=self.asset)

    @patch('shotgun_api3.Shotgun._send_form')
    def test_share_thumbnail_returns_error(self, mock_send_form):
        """throw an exception if server returns an error code"""

        mock_send_form.method.assert_called_once()
        mock_send_form.return_value = "1\nerror message.\n"

        self.assertRaises(shotgun_api3.ShotgunError, self.sg.share_thumbnail,
                          [self.version, self.shot], source_entity=self.asset)

    def test_deprecated_functions(self):
        """Deprecated functions raise errors"""
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema, "foo")
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.entity_types)

    def test_simple_summary(self):
        """Test simple call to summarize"""
        summaries = [{'field': 'id', 'type': 'count'}]
        grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summaries,
                                   grouping=grouping)
        assert(result['groups'])
        assert(result['groups'][0]['group_name'])
        assert(result['groups'][0]['group_value'])
        assert(result['groups'][0]['summaries'])
        assert(result['summaries'])

    def test_summary_include_archived_projects(self):
        """Test summarize with archived project"""
        if self.sg.server_caps.version > (5, 3, 13):
            # archive project
            self.sg.update('Project', self.project['id'], {'archived': True})
            # Ticket #25082 ability to hide archived projects in summary
            summaries = [{'field': 'id', 'type': 'count'}]
            grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
            filters = [['project', 'is', self.project]]
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_archived_projects=False)
            self.assertEqual(result['summaries']['id'],  0)
            self.sg.update('Project', self.project['id'], {'archived': False})

    def test_summary_values(self):
        """Test summarize return data"""

        # create three unique shots
        shot_prefix = uuid.uuid4().hex

        shots = []

        shot_data_1 = {
            "code": "%s Shot 1" % shot_prefix,
            "sg_status_list": "ip",
            "sg_cut_duration": 100,
            "project": self.project
        }

        shot_data_2 = {
            "code": "%s Shot 2" % shot_prefix,
            "sg_status_list": "ip",
            "sg_cut_duration": 100,
            "project": self.project
        }

        shot_data_3 = {
            "code": "%s Shot 3" % shot_prefix,
            "sg_status_list": "fin",
            "sg_cut_duration": 100,
            "project": self.project
        }

        shot_data_4 = {
            "code": "%s Shot 4" % shot_prefix,
            "sg_status_list": "wtg",
            "sg_cut_duration": 0,
            "project": self.project
        }

        shots.append(self.sg.create("Shot", shot_data_1))
        shots.append(self.sg.create("Shot", shot_data_2))
        shots.append(self.sg.create("Shot", shot_data_3))
        shots.append(self.sg.create("Shot", shot_data_4))

        summaries = [{'field': 'id', 'type': 'count'},
                     {'field': 'sg_cut_duration', 'type': 'sum'}]
        grouping = [{'direction': 'asc',
                     'field': 'sg_status_list',
                     'type': 'exact'}]
        filters = [['project', 'is', self.project],
                   ['code', 'starts_with', shot_prefix]]
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summaries,
                                   grouping=grouping)
        count = {'id': 4, 'sg_cut_duration': 300}
        groups = [
            {
                'group_name': 'fin',
                'group_value': 'fin',
                'summaries': {'id': 1, 'sg_cut_duration': 100}
            },
            {
                'group_name': 'ip',
                'group_value': 'ip',
                'summaries': {'id': 2, 'sg_cut_duration': 200}
            },
            {
                'group_name': 'wtg',
                'group_value': 'wtg',
                'summaries': {'id': 1, 'sg_cut_duration': 0}
            }
        ]
        # clean up
        batch_data = []
        for s in shots:
            batch_data.append({
                "request_type": "delete",
                                "entity_type": "Shot",
                                "entity_id": s["id"]
            })
        self.sg.batch(batch_data)

        self.assertEqual(result['summaries'], count)
        # Do not assume the order of the summarized results.
        self.assertEqual(
            sorted(
                result['groups'],
                key=lambda x: x["group_name"]
            ),
            groups
        )

    def test_ensure_ascii(self):
        '''test_ensure_ascii tests ensure_unicode flag.'''
        sg_ascii = shotgun_api3.Shotgun(self.config.server_url,
                                        self.config.script_name,
                                        self.config.api_key,
                                        ensure_ascii=True)

        result = sg_ascii.find_one('Note', [['id', 'is', self.note['id']]], fields=['content'])
        if six.PY2:
            # In Python3 there isn't a separate unicode type.
            self.assertFalse(_has_unicode(result))

    def test_ensure_unicode(self):
        '''test_ensure_unicode tests ensure_unicode flag.'''
        sg_unicode = shotgun_api3.Shotgun(self.config.server_url,
                                          self.config.script_name,
                                          self.config.api_key,
                                          ensure_ascii=False)
        result = sg_unicode.find_one('Note', [['id', 'is', self.note['id']]], fields=['content'])
        self.assertTrue(_has_unicode(result))

    def test_work_schedule(self):
        '''test_work_schedule tests WorkDayRules api'''
        self.maxDiff = None

        start_date = '2012-01-01'
        start_date_obj = datetime.datetime(2012, 1, 1)
        end_date = '2012-01-07'
        end_date_obj = datetime.datetime(2012, 1, 7)

        project = self.project
        # We're going to be comparing this value with the value returned from the server, so extract only the type, id
        # and name
        user = {"type": self.human_user["type"], "id": self.human_user["id"], "name": self.human_user["name"]}

        work_schedule = self.sg.work_schedule_read(start_date, end_date, project, user)
        # Test that the work_schedule_read api method is called with the 'start_date' and 'end_date' arguments
        # in the 'YYYY-MM-DD' string format.
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.work_schedule_read,
                          start_date_obj, end_date_obj, project, user)


        resp = self.sg.work_schedule_update('2012-01-02', False, 'Studio Holiday')
        expected = {
            'date': '2012-01-02',
            'description': 'Studio Holiday',
            'project': None,
            'user': None,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-02'] = {"reason": "STUDIO_EXCEPTION", "working": False, "description": "Studio Holiday"}
        self.assertEqual(work_schedule, resp)

        resp = self.sg.work_schedule_update('2012-01-03', False, 'Project Holiday', project)
        expected = {
            'date': '2012-01-03',
            'description': 'Project Holiday',
            'project': project,
            'user': None,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-03'] = {
            "reason": "PROJECT_EXCEPTION",
            "working": False,
            "description": "Project Holiday"
        }
        self.assertEqual(work_schedule, resp)

        jan4 = datetime.datetime(2012, 1, 4)

        self.assertRaises(shotgun_api3.ShotgunError, self.sg.work_schedule_update,
                          jan4, False, 'Artist Holiday', user=user)

        resp = self.sg.work_schedule_update("2012-01-04", False, 'Artist Holiday',  user=user)
        expected = {
            'date': '2012-01-04',
            'description': 'Artist Holiday',
            'project': None,
            'user': user,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-04'] = {"reason": "USER_EXCEPTION", "working": False, "description": "Artist Holiday"}
        self.assertEqual(work_schedule, resp)

    # For now disable tests that are erroneously failling on some sites to
    # allow CI to pass until the known issue causing this is resolved.
    # test_preferences_read fails when preferences don't match the expected
    # preferences.
    @base.skip("Skip test_preferences_read because preferences on test sites are mismatched.")
    def test_preferences_read(self):
        # Only run the tests on a server with the feature.
        if not self.sg.server_caps.version or self.sg.server_caps.version < (7, 10, 0):
            return

        # This is a big diff if it fails, so show everything.
        self.maxDiff = None

        # all prefs
        resp = self.sg.preferences_read()

        expected = {
            'date_component_order': 'month_day',
            'duration_units': 'days',
            'format_currency_fields_decimal_options': '$1,000.99',
            'format_currency_fields_display_dollar_sign': False,
            'format_currency_fields_negative_options': '- $1,000',
            'format_date_fields': '08/04/22 OR 04/08/22 (depending on the Month order preference)',
            'format_float_fields': '9,999.99',
            'format_float_fields_rounding': '9.999999',
            'format_footage_fields': '10-05',
            'format_number_fields': '1,000',
            'format_time_hour_fields': '12 hour',
            'hours_per_day': 8.0,
            'last_day_work_week': None,
            'support_local_storage': True
        }
        # Simply make sure viewmaster settings are there. These change frequently and we
        # don't want to have the test break because Viewmaster changed or because we didn't
        # update the test.
        self.assertIn("view_master_settings", resp)
        resp.pop("view_master_settings")

        self.assertEqual(expected, resp)

        # all filtered
        resp = self.sg.preferences_read(['date_component_order', 'support_local_storage'])

        expected = {
            'date_component_order': 'month_day',
            'support_local_storage': True
        }
        self.assertEqual(expected, resp)

        # all filtered with invalid pref
        resp = self.sg.preferences_read(['date_component_order', 'support_local_storage', 'email_notifications'])

        expected = {
            'date_component_order': 'month_day',
            'support_local_storage': True
        }
        self.assertEqual(expected, resp)


class TestDataTypes(base.LiveTestBase):
    '''Test fields representing the different data types mapped on the server side.

     Untested data types:  password, percent, pivot_column, serializable, image, currency
                           system_task_type, timecode, url, uuid, url_template
    '''

    def setUp(self):
        super(TestDataTypes, self).setUp()

    def test_set_checkbox(self):
        entity = 'HumanUser'
        entity_id = self.human_user['id']
        field_name = 'email_notes'
        pos_values = [False, True]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_color(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'color'
        pos_values = ['pipeline_step', '222,0,0']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_date(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'due_date'
        pos_values = ['2008-05-08', '2011-05-05']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_date_time(self):
        entity = 'HumanUser'
        entity_id = self.human_user['id']
        field_name = 'locked_until'
        local = shotgun_api3.shotgun.SG_TIMEZONE.local
        dt_1 = datetime.datetime(2008, 10, 13, 23, 10, tzinfo=local)
        dt_2 = datetime.datetime(2009, 10, 13, 23, 10, tzinfo=local)
        pos_values = [dt_1, dt_2]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_duration(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'duration'
        pos_values = [2100, 1300]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_entity(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'entity'
        pos_values = [self.asset, self.shot]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected['id'], actual['id'])

    def test_set_float(self):
        entity = 'Version'
        entity_id = self.version['id']
        field_name = 'sg_movie_aspect_ratio'
        pos_values = [2.0, 3.0]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_list(self):
        entity = 'Note'
        entity_id = self.note['id']
        field_name = 'sg_note_type'
        pos_values = ['Internal', 'Client']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_multi_entity(self):
        sg = shotgun_api3.Shotgun(self.config.server_url,
                                  self.config.script_name,
                                  self.config.api_key)
        keys = ['project', 'user', 'code']
        data = {'project': self.project,
                'user': self.human_user,
                'code': 'Alpha'}
        version_1 = base._find_or_create_entity(sg, 'Version', data, keys)
        data = {'project': self.project,
                'user': self.human_user,
                'code': 'Beta'}
        version_2 = base._find_or_create_entity(sg, 'Version', data, keys)

        entity = 'Playlist'
        entity_id = self.playlist['id']
        field_name = 'versions'

        # Default set behaviour
        pos_values = [[version_1, version_2]]
        expected, actual = self.assert_set_field(entity, entity_id, field_name, pos_values)
        self.assertEqual(len(expected), len(actual))
        self.assertEqual(
            sorted([x['id'] for x in expected]),
            sorted([x['id'] for x in actual])
        )

        # Multi-entity remove mode
        pos_values = [[version_1]]
        expected, actual = self.assert_set_field(entity, entity_id, field_name, pos_values,
                                                 multi_entity_update_mode='remove')
        self.assertEqual(1, len(actual))
        self.assertEqual(len(expected), len(actual))
        self.assertNotEqual(expected[0]['id'], actual[0]['id'])
        self.assertEqual(version_2['id'], actual[0]['id'])

        # Multi-entity add mode
        pos_values = [[version_1]]
        expected, actual = self.assert_set_field(entity, entity_id, field_name, pos_values,
                                                 multi_entity_update_mode='add')
        self.assertEqual(2, len(actual))
        self.assertTrue(version_1['id'] in [x['id'] for x in actual])

        # Multi-entity set mode
        pos_values = [[version_1, version_2]]
        expected, actual = self.assert_set_field(entity, entity_id, field_name, pos_values,
                                                 multi_entity_update_mode='set')
        self.assertEqual(len(expected), len(actual))
        self.assertEqual(
            sorted([x['id'] for x in expected]),
            sorted([x['id'] for x in actual])
        )

    def test_set_number(self):
        entity = 'Shot'
        entity_id = self.shot['id']
        field_name = 'head_in'
        pos_values = [2300, 1300]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_status_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'sg_status_list'
        pos_values = ['wtg', 'fin']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_tag_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'tag_list'
        pos_values = [['a', 'b'], ['c']]
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_text(self):
        entity = 'Note'
        entity_id = self.note['id']
        field_name = 'content'
        pos_values = ['this content', 'that content']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_text_html_entity(self):
        entity = 'Note'
        entity_id = self.note['id']
        field_name = 'content'
        pos_values = ['<', '<']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def assert_set_field(self, entity, entity_id, field_name, pos_values, multi_entity_update_mode=None):
        query_result = self.sg.find_one(entity,
                                        [['id', 'is', entity_id]],
                                        [field_name])
        initial_value = query_result[field_name]
        new_value = (initial_value == pos_values[0] and pos_values[1]) or pos_values[0]
        if multi_entity_update_mode:
            self.sg.update(entity, entity_id, {field_name: new_value},
                           multi_entity_update_modes={field_name: multi_entity_update_mode})
        else:
            self.sg.update(entity, entity_id, {field_name: new_value})
        new_values = self.sg.find_one(entity,
                                      [['id', 'is', entity_id]],
                                      [field_name])
        return new_value, new_values[field_name]


class TestUtc(base.LiveTestBase):
    '''Test utc options'''

    def setUp(self):
        super(TestUtc, self).setUp()
        utc = shotgun_api3.shotgun.SG_TIMEZONE.utc
        self.datetime_utc = datetime.datetime(2008, 10, 13, 23, 10, tzinfo=utc)
        local = shotgun_api3.shotgun.SG_TIMEZONE.local
        self.datetime_local = datetime.datetime(2008, 10, 13, 23, 10, tzinfo=local)
        self.datetime_none = datetime.datetime(2008, 10, 13, 23, 10)

    def test_convert_to_utc(self):
        sg_utc = shotgun_api3.Shotgun(self.config.server_url,
                                      self.config.script_name,
                                      self.config.api_key,
                                      http_proxy=self.config.http_proxy,
                                      convert_datetimes_to_utc=True)
        self._assert_expected(sg_utc, self.datetime_none, self.datetime_local)
        self._assert_expected(sg_utc, self.datetime_local, self.datetime_local)

    def test_no_convert_to_utc(self):
        sg_no_utc = shotgun_api3.Shotgun(self.config.server_url,
                                         self.config.script_name,
                                         self.config.api_key,
                                         http_proxy=self.config.http_proxy,
                                         convert_datetimes_to_utc=False)
        self._assert_expected(sg_no_utc, self.datetime_none, self.datetime_none)
        self._assert_expected(sg_no_utc, self.datetime_utc, self.datetime_none)

    def _assert_expected(self, sg, date_time, expected):
        entity_name = 'HumanUser'
        entity_id = self.human_user['id']
        field_name = 'locked_until'
        sg.update(entity_name, entity_id, {field_name: date_time})
        result = sg.find_one(entity_name, [['id', 'is', entity_id]], [field_name])
        self.assertEqual(result[field_name], expected)


class TestFind(base.LiveTestBase):
    def setUp(self):
        super(TestFind, self).setUp()
        # We will need the created_at field for the shot
        fields = list(self.shot.keys())[:]
        fields.append('created_at')
        self.shot = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]], fields)
        # We will need the uuid field for our LocalStorage
        fields = list(self.local_storage.keys())[:]
        fields.append('uuid')
        self.local_storage = self.sg.find_one('LocalStorage', [['id', 'is', self.local_storage['id']]], fields)

    def test_find(self):
        """Called find, find_one for known entities"""
        filters = []
        filters.append(['project', 'is', self.project])
        filters.append(['id', 'is', self.version['id']])

        fields = ['id']

        versions = self.sg.find("Version", filters, fields=fields)

        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

    def _id_in_result(self, entity_type, filters, expected_id):
        """
        Checks that a given id matches that of entities returned
        for particular filters.
        """
        results = self.sg.find(entity_type, filters)
        return any(result['id'] == expected_id for result in results)

    # TODO test all applicable data types for 'in'
        # 'currency' => [BigDecimal, Float, NilClass],
        # 'image' => [Hash, NilClass],
        # 'percent' => [Bignum, Fixnum, NilClass],
        # 'serializable' => [Hash, Array, NilClass],
        # 'system_task_type' => [String, NilClass],
        # 'timecode' => [Bignum, Fixnum, NilClass],
        # 'footage' => [Bignum, Fixnum, NilClass, String, Float, BigDecimal],
        # 'url' => [Hash, NilClass],

        # 'uuid' => [String],

    def test_in_relation_comma_id(self):
        """
        Test that 'in' relation using commas (old format) works with ids.
        """
        filters = [['id', 'in', self.project['id'], 99999]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_in_relation_list_id(self):
        """
        Test that 'in' relation using list (new format) works with ids.
        """
        filters = [['id', 'in', [self.project['id'], 99999]]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_not_in_relation_id(self):
        """
        Test that 'not_in' relation using commas (old format) works with ids.
        """
        filters = [['id', 'not_in', self.project['id'], 99999]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertFalse(result)

    def test_in_relation_comma_text(self):
        """
        Test that 'in' relation using commas (old format) works with text fields.
        """
        filters = [['name', 'in', self.project['name'], 'fake project name']]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_in_relation_list_text(self):
        """
        Test that 'in' relation using list (new format) works with text fields.
        """
        filters = [['name', 'in', [self.project['name'], 'fake project name']]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertTrue(result)

    def test_not_in_relation_text(self):
        """
        Test that 'not_in' relation using commas (old format) works with ids.
        """
        filters = [['name', 'not_in', [self.project['name'], 'fake project name']]]
        result = self._id_in_result('Project', filters, self.project['id'])
        self.assertFalse(result)

    def test_in_relation_comma_color(self):
        """
        Test that 'in' relation using commas (old format) works with color fields.
        """
        filters = [['color', 'in', self.task['color'], 'Green'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_color(self):
        """
        Test that 'in' relation using list (new format) works with color fields.
        """
        filters = [['color', 'in', [self.task['color'], 'Green']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_color(self):
        """
        Test that 'not_in' relation using commas (old format) works with color fields.
        """
        filters = [['color', 'not_in', [self.task['color'], 'Green']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_date(self):
        """
        Test that 'in' relation using commas (old format) works with date fields.
        """
        filters = [['due_date', 'in', self.task['due_date'], '2012-11-25'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_date(self):
        """
        Test that 'in' relation using list (new format) works with date fields.
        """
        filters = [['due_date', 'in', [self.task['due_date'], '2012-11-25']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_date(self):
        """
        Test that 'not_in' relation using commas (old format) works with date fields.
        """
        filters = [['due_date', 'not_in', [self.task['due_date'], '2012-11-25']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    # TODO add datetime test for in and not_in

    def test_in_relation_comma_duration(self):
        """
        Test that 'in' relation using commas (old format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = list(self.task.keys())[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task', [['id', 'is', self.task['id']]], new_task_keys)
        filters = [['duration', 'in', self.task['duration']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_duration(self):
        """
        Test that 'in' relation using list (new format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = list(self.task.keys())[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task', [['id', 'is', self.task['id']]], new_task_keys)
        filters = [['duration', 'in', [self.task['duration'], ]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_duration(self):
        """
        Test that 'not_in' relation using commas (old format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = list(self.task.keys())[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task', [['id', 'is', self.task['id']]], new_task_keys)

        filters = [['duration', 'not_in', [self.task['duration'], ]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_entity(self):
        """
        Test that 'in' relation using commas (old format) works with entity fields.
        """
        filters = [['entity', 'in', self.task['entity'], self.asset],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_entity(self):
        """
        Test that 'in' relation using list (new format) works with entity fields.
        """
        filters = [['entity', 'in', [self.task['entity'], self.asset]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_entity(self):
        """
        Test that 'not_in' relation using commas (old format) works with entity fields.
        """
        filters = [['entity', 'not_in', [self.task['entity'], self.asset]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_entity_type(self):
        """
        Test that 'in' relation using commas (old format) works with entity_type fields.
        """
        filters = [['entity_type', 'in', self.step['entity_type'], 'something else']]

        result = self._id_in_result('Step', filters, self.step['id'])
        self.assertTrue(result)

    def test_in_relation_list_entity_type(self):
        """
        Test that 'in' relation using list (new format) works with entity_type fields.
        """
        filters = [['entity_type', 'in', [self.step['entity_type'], 'something else']]]

        result = self._id_in_result('Step', filters, self.step['id'])
        self.assertTrue(result)

    def test_not_in_relation_entity_type(self):
        """
        Test that 'not_in' relation using commas (old format) works with entity_type fields.
        """
        filters = [['entity_type', 'not_in', [self.step['entity_type'], 'something else']]]

        result = self._id_in_result('Step', filters, self.step['id'])
        self.assertFalse(result)

    def test_in_relation_comma_float(self):
        """
        Test that 'in' relation using commas (old format) works with float fields.
        """
        filters = [['sg_frames_aspect_ratio', 'in', self.version['sg_frames_aspect_ratio'], 44.0],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_in_relation_list_float(self):
        """
        Test that 'in' relation using list (new format) works with float fields.
        """
        filters = [['sg_frames_aspect_ratio', 'in', [self.version['sg_frames_aspect_ratio'], 30.0]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_not_in_relation_float(self):
        """
        Test that 'not_in' relation using commas (old format) works with float fields.
        """
        filters = [['sg_frames_aspect_ratio', 'not_in', [self.version['sg_frames_aspect_ratio'], 4.4]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertFalse(result)

    def test_in_relation_comma_list(self):
        """
        Test that 'in' relation using commas (old format) works with list fields.
        """
        filters = [['sg_priority', 'in', self.ticket['sg_priority'], '1'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Ticket', filters, self.ticket['id'])
        self.assertTrue(result)

    def test_in_relation_list_list(self):
        """
        Test that 'in' relation using list (new format) works with list fields.
        """
        filters = [['sg_priority', 'in', [self.ticket['sg_priority'], '1']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Ticket', filters, self.ticket['id'])
        self.assertTrue(result)

    def test_not_in_relation_list(self):
        """
        Test that 'not_in' relation using commas (old format) works with list fields.
        """
        filters = [['sg_priority', 'not_in', [self.ticket['sg_priority'], '1']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Ticket', filters, self.ticket['id'])
        self.assertFalse(result)

    def test_in_relation_comma_multi_entity(self):
        """
        Test that 'in' relation using commas (old format) works with multi_entity fields.
        """
        filters = [['task_assignees', 'in', self.human_user, ],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_multi_entity(self):
        """
        Test that 'in' relation using list (new format) works with multi_entity fields.
        """
        filters = [['task_assignees', 'in', [self.human_user, ]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_multi_entity(self):
        """
        Test that 'not_in' relation using commas (old format) works with multi_entity fields.
        """
        filters = [['task_assignees', 'not_in', [self.human_user, ]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_number(self):
        """
        Test that 'in' relation using commas (old format) works with number fields.
        """
        filters = [['frame_count', 'in', self.version['frame_count'], 1],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_in_relation_list_number(self):
        """
        Test that 'in' relation using list (new format) works with number fields.
        """
        filters = [['frame_count', 'in', [self.version['frame_count'], 1]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertTrue(result)

    def test_not_in_relation_number(self):
        """
        Test that 'not_in' relation using commas (old format) works with number fields.
        """
        filters = [['frame_count', 'not_in', [self.version['frame_count'], 1]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Version', filters, self.version['id'])
        self.assertFalse(result)

    def test_in_relation_comma_status_list(self):
        """
        Test that 'in' relation using commas (old format) works with status_list fields.
        """
        filters = [['sg_status_list', 'in', self.task['sg_status_list'], 'fin'],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_status_list(self):
        """
        Test that 'in' relation using list (new format) works with status_list fields.
        """
        filters = [['sg_status_list', 'in', [self.task['sg_status_list'], 'fin']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_status_list(self):
        """
        Test that 'not_in' relation using commas (old format) works with status_list fields.
        """
        filters = [['sg_status_list', 'not_in', [self.task['sg_status_list'], 'fin']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertFalse(result)

    def test_in_relation_comma_uuid(self):
        """
        Test that 'in' relation using commas (old format) works with uuid fields.
        """
        filters = [['uuid', 'in', self.local_storage['uuid'], ]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertTrue(result)

    def test_in_relation_list_uuid(self):
        """
        Test that 'in' relation using list (new format) works with uuid fields.
        """
        filters = [['uuid', 'in', [self.local_storage['uuid'], ]]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertTrue(result)

    def test_not_in_relation_uuid(self):
        """
        Test that 'not_in' relation using commas (old format) works with uuid fields.
        """
        filters = [['uuid', 'not_in', [self.local_storage['uuid'], ]]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertFalse(result)

    def test_find_in(self):
        """Test use of 'in' relation with find."""
        # id
        # old comma seperated format
        filters = [['id', 'in', self.project['id'], 99999]]
        projects = self.sg.find('Project', filters)
        # can't use 'any' in py 2.4
        match = False
        for project in projects:
            if project['id'] == self.project['id']:
                match = True
        self.assertTrue(match)

        # new list format
        filters = [['id', 'in', [self.project['id'], 99999]]]
        projects = self.sg.find('Project', filters)
        # can't use 'any' in py 2.4
        match = False
        for project in projects:
            if project['id'] == self.project['id']:
                match = True
        self.assertTrue(match)

        # text field
        filters = [['name', 'in', [self.project['name'], 'fake project name']]]
        projects = self.sg.find('Project', filters)
        project = projects[0]
        self.assertEqual(self.project['id'], project['id'])

    def test_unsupported_filters(self):
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'Shot',
                          [['image', 'is_not', [{"type": "Thumbnail", "id": 9}]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'HumanUser', [['password_proxy', 'is_not', [None]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'EventLogEntry', [['meta', 'is_not', [None]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'Revision', [['meta', 'attachment', [None]]])

    def test_zero_is_not_none(self):
        '''Test the zero and None are differentiated using "is_not" filter.
           Ticket #25127
        '''
        # Create a number field if it doesn't already exist
        num_field = 'sg_api_tests_number_field'
        if num_field not in list(self.sg.schema_field_read('Asset').keys()):
            self.sg.schema_field_create('Asset', 'number', num_field.replace('sg_', '').replace('_', ' '))

        # Set to None
        self.sg.update('Asset', self.asset['id'], {num_field: None})

        # Should be filtered out
        result = self.sg.find('Asset', [['id', 'is', self.asset['id']], [num_field, 'is_not', None]], [num_field])
        self.assertEqual([], result)

        # Set it to zero
        self.sg.update('Asset', self.asset['id'], {num_field: 0})

        # Should not be filtered out
        result = self.sg.find_one('Asset', [['id', 'is', self.asset['id']], [num_field, 'is_not', None]], [num_field])
        self.assertFalse(result is None)

        # Set it to some other number
        self.sg.update('Asset', self.asset['id'], {num_field: 1})

        # Should not be filtered out
        result = self.sg.find_one('Asset', [['id', 'is', self.asset['id']], [num_field, 'is_not', None]], [num_field])
        self.assertFalse(result is None)

    def test_include_archived_projects(self):
        if self.sg.server_caps.version > (5, 3, 13):
            # Ticket #25082
            result = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]])
            self.assertEqual(self.shot['id'], result['id'])

            # archive project
            self.sg.update('Project', self.project['id'], {'archived': True})

            # setting defaults to True, so we should get result
            result = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]])
            self.assertEqual(self.shot['id'], result['id'])

            result = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]], include_archived_projects=False)
            self.assertEqual(None, result)

            # unarchive project
            self.sg.update('Project', self.project['id'], {'archived': False})


class TestFollow(base.LiveTestBase):

    def test_follow_unfollow(self):
        '''Test follow method'''

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return

        with self.gen_entity(
            "HumanUser",
            projects=[self.project],
        ) as human_user, self.gen_entity(
            "Shot",
            project=self.project,
        ) as shot:
            result = self.sg.follow(human_user, shot)
            assert(result['followed'])

            result = self.sg.unfollow(human_user, shot)
            assert(result['unfollowed'])

    def test_followers(self):
        '''Test followers method'''

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return

        with self.gen_entity(
            "HumanUser",
            projects=[self.project],
        ) as human_user, self.gen_entity(
            "Shot",
            project=self.project,
        ) as shot:
            result = self.sg.follow(human_user, shot)
            assert(result['followed'])

            result = self.sg.followers(shot)

            self.assertEqual(1, len(result))
            self.assertEqual(human_user['id'], result[0]['id'])

    def test_following(self):
        '''Test following method'''

        if not self.sg.server_caps.version or self.sg.server_caps.version < (7, 0, 12):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        with self.gen_entity(
            "HumanUser",
            projects=[self.project],
        ) as human_user, self.gen_entity(
            "Shot",
            project=self.project,
        ) as shot, self.gen_entity(
            "Task",
            project=self.project,
        ) as task:
            result = self.sg.follow(human_user, shot)
            assert(result['followed'])

            result = self.sg.following(human_user)

            self.assertEqual(1, len(result))

            result = self.sg.follow(human_user, task)
            assert(result['followed'])

            result = self.sg.following(human_user)

            self.assertEqual(2, len(result))
            result = self.sg.following(human_user, entity_type="Task")
            self.assertEqual(1, len(result))
            result = self.sg.following(human_user, entity_type="Shot")
            self.assertEqual(1, len(result))

            shot_project_id = self.sg.find_one("Shot",
                                            [["id", "is", shot["id"]]],
                                            ["project.Project.id"])["project.Project.id"]
            task_project_id = self.sg.find_one("Task",
                                            [["id", "is", task["id"]]],
                                            ["project.Project.id"])["project.Project.id"]
            project_count = 2 if shot_project_id == task_project_id else 1
            result = self.sg.following(human_user, project={"type": "Project", "id": shot_project_id})
            self.assertEqual(project_count, len(result))
            result = self.sg.following(human_user, project={"type": "Project", "id": task_project_id})
            self.assertEqual(project_count, len(result))
            result = self.sg.following(human_user,
                                    project={"type": "Project", "id": shot_project_id},
                                    entity_type="Shot")
            self.assertEqual(1, len(result))
            result = self.sg.following(human_user,
                                    project={"type": "Project", "id": task_project_id},
                                    entity_type="Task")
            self.assertEqual(1, len(result))


class TestErrors(base.TestBase):
    def test_bad_auth(self):
        '''test_bad_auth invalid script name or api key raises fault'''
        server_url = self.config.server_url
        script_name = 'not_real_script_name'
        api_key = self.config.api_key
        login = self.config.human_login
        password = self.config.human_password
        auth_token = "111111"

        # Test various combinations of illegal arguments
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, None, api_key)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, None)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name,
                          api_key, login=login, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, login=login)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, login=login, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, login=login, auth_token=auth_token)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, password=password, auth_token=auth_token)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, login=login,
                          password=password, auth_token=auth_token)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, api_key=api_key, login=login,
                          password=password, auth_token=auth_token)

        # Test failed authentications
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.AuthenticationFault, sg.find_one, 'Shot', [])

        script_name = self.config.script_name
        api_key = 'notrealapikey'
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.AuthenticationFault, sg.find_one, 'Shot', [])

        sg = shotgun_api3.Shotgun(server_url, login=login, password='not a real password')
        self.assertRaises(shotgun_api3.AuthenticationFault, sg.find_one, 'Shot', [])

        # This may trigger an account lockdown. Make sure it is not locked anymore.
        user = self.sg.find_one("HumanUser", [["login", "is", login]])
        self.sg.update("HumanUser", user["id"], {"locked_until": None})

    @patch('shotgun_api3.shotgun.Http.request')
    def test_status_not_200(self, mock_request):
        response = MagicMock(name="response mock", spec=dict)
        response.status = 300
        response.reason = 'reason'
        mock_request.return_value = (response, {})
        self.assertRaises(shotgun_api3.ProtocolError, self.sg.find_one, 'Shot', [])

    @patch('shotgun_api3.shotgun.Http.request')
    def test_sha2_error(self, mock_request):
        # Simulate the exception raised with SHA-2 errors
        mock_request.side_effect = ShotgunSSLError(
            "[Errno 1] _ssl.c:480: error:0D0C50A1:asn1 "
            "encoding routines:ASN1_item_verify: unknown message digest "
            "algorithm"
        )

        # save the original state
        original_env_val = os.environ.pop("SHOTGUN_FORCE_CERTIFICATE_VALIDATION", None)

        # ensure we're starting with the right values
        self.sg.reset_user_agent()

        # ensure the initial settings are correct. These will be different depending on whether
        # the ssl module imported successfully or not.
        if "ssl" in sys.modules:
            self.assertFalse(self.sg.config.no_ssl_validation)
            self.assertFalse(shotgun_api3.shotgun.NO_SSL_VALIDATION)
            self.assertTrue("(validate)" in " ".join(self.sg._user_agents))
            self.assertFalse("(no-validate)" in " ".join(self.sg._user_agents))
        else:
            self.assertTrue(self.sg.config.no_ssl_validation)
            self.assertTrue(shotgun_api3.shotgun.NO_SSL_VALIDATION)
            self.assertFalse("(validate)" in " ".join(self.sg._user_agents))
            self.assertTrue("(no-validate)" in " ".join(self.sg._user_agents))

        try:
            self.sg.info()
        except ShotgunSSLError:
            # ensure the api has reset the values in the correct fallback behavior
            self.assertTrue(self.sg.config.no_ssl_validation)
            self.assertTrue(shotgun_api3.shotgun.NO_SSL_VALIDATION)
            self.assertFalse("(validate)" in " ".join(self.sg._user_agents))
            self.assertTrue("(no-validate)" in " ".join(self.sg._user_agents))

        if original_env_val is not None:
            os.environ["SHOTGUN_FORCE_CERTIFICATE_VALIDATION"] = original_env_val

    @patch('shotgun_api3.shotgun.Http.request')
    def test_sha2_error_with_strict(self, mock_request):
        # Simulate the exception raised with SHA-2 errors
        mock_request.side_effect = ShotgunSSLError(
            "[Errno 1] _ssl.c:480: error:0D0C50A1:asn1 "
            "encoding routines:ASN1_item_verify: unknown message digest "
            "algorithm"
        )

        # save the original state
        original_env_val = os.environ.pop("SHOTGUN_FORCE_CERTIFICATE_VALIDATION", None)
        os.environ["SHOTGUN_FORCE_CERTIFICATE_VALIDATION"] = "1"

        # ensure we're starting with the right values
        self.sg.config.no_ssl_validation = False
        shotgun_api3.shotgun.NO_SSL_VALIDATION = False
        self.sg.reset_user_agent()

        try:
            self.sg.info()
        except ShotgunSSLError:
            # ensure the api has NOT reset the values in the fallback behavior because we have
            # set the env variable to force validation
            self.assertFalse(self.sg.config.no_ssl_validation)
            self.assertFalse(shotgun_api3.shotgun.NO_SSL_VALIDATION)
            self.assertFalse("(no-validate)" in " ".join(self.sg._user_agents))
            self.assertTrue("(validate)" in " ".join(self.sg._user_agents))

        if original_env_val is not None:
            os.environ["SHOTGUN_FORCE_CERTIFICATE_VALIDATION"] = original_env_val

    @patch.object(urllib.request.OpenerDirector, 'open')
    def test_sanitized_auth_params(self, mock_open):
        # Simulate the server blowing up and giving us a 500 error
        mock_open.side_effect = urllib.error.HTTPError('url', 500, 'message', {}, None)

        this_dir, _ = os.path.split(__file__)
        thumbnail_path = os.path.abspath(os.path.join(this_dir, "sg_logo.jpg"))

        try:
            # Try to upload a bogus file
            self.sg.upload('Note', 1234, thumbnail_path)
        except shotgun_api3.ShotgunError as e:
            self.assertFalse(self.api_key in str(e))
            return

        # You should never get here... Otherwise some mocking failed and the
        # except above wasn't properly run
        self.assertTrue(False)

    def test_upload_empty_file(self):
        """
        Test uploading an empty file raises an error.
        """
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(os.path.join(this_dir, "empty.txt")))
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.upload, 'Version', 123, path)
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.upload_thumbnail, 'Version', 123, path)
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.upload_filmstrip_thumbnail, 'Version',
                          123, path)

    def test_upload_missing_file(self):
        """
        Test uploading an missing file raises an error.
        """
        path = "/path/to/nowhere/foo.txt"
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.upload, 'Version', 123, path)
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.upload_thumbnail, 'Version', 123, path)
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.upload_filmstrip_thumbnail, 'Version',
                          123, path)

#    def test_malformed_response(self):
#        # TODO ResponseError
#        pass


class TestScriptUserSudoAuth(base.LiveTestBase):
    def setUp(self):
        super(TestScriptUserSudoAuth, self).setUp('ApiUser')

        self.sg.update(
            'HumanUser',
            self.human_user['id'],
            {'projects': [self.project]},
        )

    def test_user_is_creator(self):
        """
        Test 'sudo_as_login' option: on create, ensure appropriate user is set in created-by
        """

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 3, 12):
            return

        x = shotgun_api3.Shotgun(self.config.server_url,
                                 self.config.script_name,
                                 self.config.api_key,
                                 http_proxy=self.config.http_proxy,
                                 sudo_as_login=self.config.human_login)

        data = {
            'project': self.project,
            'code': 'JohnnyApple_Design01_FaceFinal',
            'description': 'fixed rig per director final notes',
            'sg_status_list': 'na',
            'entity': self.asset,
            'user': self.human_user
        }

        version = x.create("Version", data, return_fields=["id", "created_by"])
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        self.assertTrue("created_by" in version)
        self.assertEqual(self.config.human_name, version['created_by']['name'])


class TestHumanUserSudoAuth(base.TestBase):
    def setUp(self):
        super(TestHumanUserSudoAuth, self).setUp('HumanUser')

    def test_human_user_sudo_auth_fails(self):
        """
        Test 'sudo_as_login' option for HumanUser.
        Request fails on server because user has no permission to Sudo.
        """

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 3, 12):
            return

        x = shotgun_api3.Shotgun(self.config.server_url,
                                 login=self.config.human_login,
                                 password=self.config.human_password,
                                 http_proxy=self.config.http_proxy,
                                 sudo_as_login="blah")
        self.assertRaises(shotgun_api3.Fault, x.find_one, 'Shot', [])
        expected = "The user does not have permission to 'sudo':"
        try:
            x.find_one('Shot', [])
        except shotgun_api3.Fault as e:
            # py24 exceptions don't have message attr
            if hasattr(e, 'message'):
                self.assertTrue(e.message.startswith(expected))
            else:
                self.assertTrue(e.args[0].startswith(expected))


class TestHumanUserAuth(base.HumanUserAuthLiveTestBase):
    """
    Testing the username/password authentication method
    """

    def test_humanuser_find(self):
        """Called find, find_one for known entities as human user"""
        filters = []
        filters.append(['project', 'is', self.project])
        filters.append(['id', 'is', self.version['id']])

        fields = ['id']

        versions = self.sg.find("Version", filters, fields=fields)

        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

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
        self.assertIn(thumb_resp['status'], ['200', '304'])
        self.assertIn(thumb_resp['content-type'], ['image/jpeg', 'image/png'])

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version", self.version['id'], {'image': None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)


class TestSessionTokenAuth(base.SessionTokenAuthLiveTestBase):
    """
    Testing the session token based authentication method
    """

    def test_humanuser_find(self):
        """Called find, find_one for known entities as session token based user"""

        if self.sg.server_caps.version >= (5, 4, 1):

            filters = []
            filters.append(['project', 'is', self.project])
            filters.append(['id', 'is', self.version['id']])

            fields = ['id']

            versions = self.sg.find("Version", filters, fields=fields)

            self.assertTrue(isinstance(versions, list))
            version = versions[0]
            self.assertEqual("Version", version["type"])
            self.assertEqual(self.version['id'], version["id"])

            version = self.sg.find_one("Version", filters, fields=fields)
            self.assertEqual("Version", version["type"])
            self.assertEqual(self.version['id'], version["id"])

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
            self.assertIn(thumb_resp['status'], ['200', '304'])
            self.assertIn(thumb_resp['content-type'], ['image/jpeg', 'image/png'])

            # clear thumbnail
            response_clear_thumbnail = self.sg.update("Version", self.version['id'], {'image': None})
            expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
            self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)


class TestProjectLastAccessedByCurrentUser(base.LiveTestBase):
    # Ticket #24681
    def test_logged_in_user(self):
        if self.sg.server_caps.version and self.sg.server_caps.version < (5, 3, 20):
            return

        sg = shotgun_api3.Shotgun(self.config.server_url,
                                  login=self.config.human_login,
                                  password=self.config.human_password,
                                  http_proxy=self.config.http_proxy)

        sg.update_project_last_accessed(self.project)
        initial = sg.find_one('Project', [['id', 'is', self.project['id']]], ['last_accessed_by_current_user'])

        # Make sure time has elapsed so there is a difference between the two time stamps.
        time.sleep(2)

        sg.update_project_last_accessed(self.project)

        current = sg.find_one('Project', [['id', 'is', self.project['id']]], ['last_accessed_by_current_user'])
        self.assertNotEqual(initial, current)
        # it's possible initial is None
        assert(initial['last_accessed_by_current_user'] < current['last_accessed_by_current_user'])

    def test_pass_in_user(self):
        if self.sg.server_caps.version and self.sg.server_caps.version < (5, 3, 20):
            return

        sg = shotgun_api3.Shotgun(self.config.server_url,
                                  login=self.config.human_login,
                                  password=self.config.human_password,
                                  http_proxy=self.config.http_proxy)

        initial = sg.find_one('Project', [['id', 'is', self.project['id']]], ['last_accessed_by_current_user'])
        time.sleep(1)

        # this instance of the api is not logged in as a user
        self.sg.update_project_last_accessed(self.project, user=self.human_user)

        current = sg.find_one('Project', [['id', 'is', self.project['id']]], ['last_accessed_by_current_user'])
        self.assertNotEqual(initial, current)
        # it's possible initial is None
        if initial:
            assert(initial['last_accessed_by_current_user'] < current['last_accessed_by_current_user'])

    def test_sudo_as_user(self):
        if self.sg.server_caps.version and self.sg.server_caps.version < (5, 3, 20):
            return

        sg = shotgun_api3.Shotgun(self.config.server_url,
                                  self.config.script_name,
                                  self.config.api_key,
                                  http_proxy=self.config.http_proxy,
                                  sudo_as_login=self.config.human_login)

        initial = sg.find_one('Project', [['id', 'is', self.project['id']]], ['last_accessed_by_current_user'])
        time.sleep(1)

        sg.update_project_last_accessed(self.project)

        current = sg.find_one('Project', [['id', 'is', self.project['id']]], ['last_accessed_by_current_user'])
        self.assertNotEqual(initial, current)
        # it's possible initial is None
        if initial:
            assert(initial['last_accessed_by_current_user'] < current['last_accessed_by_current_user'])


class TestActivityStream(base.LiveTestBase):
    """
    Unit tests for the activity_stream_read() method
    """

    def setUp(self):
        super(TestActivityStream, self).setUp()
        self._prefix = uuid.uuid4().hex

        self._shot = self.sg.create("Shot", {"code": "%s activity stream test" % self._prefix,
                                             "project": self.project})

        self._note = self.sg.create("Note", {"content": "Test!",
                                             "project": self.project,
                                             "note_links": [self._shot]})

        # check that if the created_by is a script user, we want to ensure
        # that event log generation is enabled for this user. If it has been
        # disabled, these tests will fail because the activity stream is
        # connected to events. In this case, print a warning to the user
        d = self.sg.find_one("Shot",
                             [["id", "is", self._shot["id"]]],
                             ["created_by.ApiUser.generate_event_log_entries"])

        if d["created_by.ApiUser.generate_event_log_entries"] is False:
            # events are turned off! warn the user
            print("WARNING! Looks like the script user that is running these "
                  "tests has got the generate event log entries setting set to "
                  "off. This will cause the activity stream tests to fail. "
                  "Please enable event log generation for the script user.")

    def tearDown(self):
        batch_data = []
        batch_data.append({"request_type": "delete",
                           "entity_type": self._note["type"],
                           "entity_id": self._note["id"]})
        batch_data.append({"request_type": "delete",
                           "entity_type": self._shot["type"],
                           "entity_id": self._shot["id"]})
        self.sg.batch(batch_data)

        super(TestActivityStream, self).tearDown()

    def test_simple(self):
        """
        Test activity stream
        """

        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.activity_stream_read(self._shot["type"],
                                              self._shot["id"])

        expected_keys = ["earliest_update_id",
                         "entity_id",
                         "entity_type",
                         "latest_update_id",
                         "updates"]

        self.assertEqual(set(expected_keys), set(result.keys()))
        self.assertEqual(len(result["updates"]), 2)
        self.assertEqual(result["entity_type"], "Shot")
        self.assertEqual(result["entity_id"], self._shot["id"])

    def test_limit(self):
        """
        Test limited activity stream
        """

        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.activity_stream_read(self._shot["type"],
                                              self._shot["id"],
                                              limit=1)

        self.assertEqual(len(result["updates"]), 1)
        self.assertEqual(result["updates"][0]["update_type"], "create")
        self.assertEqual(result["updates"][0]["meta"]["entity_type"], "Note")

    def test_extra_fields(self):
        """
        Test additional fields for activity stream
        """

        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.activity_stream_read(self._shot["type"],
                                              self._shot["id"],
                                              entity_fields={"Shot": ["created_by.HumanUser.image"],
                                                             "Note": ["content"]})

        self.assertEqual(len(result["updates"]), 2)
        self.assertEqual(set(result["updates"][0]["primary_entity"].keys()),
                         set(["content",
                              "id",
                              "name",
                              "status",
                              "type"]))

        self.assertEqual(set(result["updates"][1]["primary_entity"].keys()),
                         set(["created_by.HumanUser.image",
                              "id",
                              "name",
                              "status",
                              "type"]))


class TestNoteThreadRead(base.LiveTestBase):
    """
    Unit tests for the note_thread_read method
    """

    def setUp(self):
        super(TestNoteThreadRead, self).setUp()

        # get path to our std attahcment
        this_dir, _ = os.path.split(__file__)
        self._thumbnail_path = os.path.abspath(os.path.join(this_dir, "sg_logo.jpg"))

    def _check_note(self, data, note_id, additional_fields):

        # check the expected fields
        expected_fields = set(["content", "created_at", "created_by", "id", "type"] + additional_fields)

        self.assertEqual(expected_fields, set(data.keys()))

        # check that the data matches the data we get from a find call
        note_data = self.sg.find_one("Note",
                                     [["id", "is", note_id]],
                                     list(expected_fields))
        self.assertEqual(note_data, data)

    def _check_reply(self, data, reply_id, additional_fields):

        # check the expected fields
        expected_fields = set(["content", "created_at", "user", "id", "type"] + additional_fields)
        self.assertEqual(expected_fields, set(data.keys()))

        # check that the data matches the data we get from a find call
        reply_data = self.sg.find_one("Reply",
                                      [["id", "is", reply_id]],
                                      list(expected_fields))

        # the reply stream adds an image to the user fields in order
        # to include thumbnails for users, so remove this before we compare
        # against the shotgun find data. The image is tested elsewhere.
        del data["user"]["image"]

        self.assertEqual(reply_data, data)

    def _check_attachment(self, data, attachment_id, additional_fields):
        # check the expected fields
        expected_fields = set(["created_at", "created_by", "id", "type"] + additional_fields)
        self.assertEqual(expected_fields, set(data.keys()))

        # check that the data matches the data we get from a find call
        attachment_data = self.sg.find_one("Attachment",
                                           [["id", "is", attachment_id]],
                                           list(expected_fields))

        self.assertEqual(attachment_data, data)

    # For now skip tests that are erroneously failling on some sites to
    # allow CI to pass until the known issue causing this is resolved.
    @base.skip("Skipping test that erroneously fails on some sites.")
    def test_simple(self):
        """
        Test note reply thread API call
        """
        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        # create note
        note = self.sg.create("Note", {"content": "Test!", "project": self.project})

        # for this test, we check that the replies returned also
        # contain the thumbnail associated with the user doing the
        # reply. For this, make sure that there is a thumbnail
        # associated with the current user

        d = self.sg.find_one("Note",
                             [["id", "is", note["id"]]],
                             ["created_by", "created_by.ApiUser.image"])

        current_thumbnail = d["created_by.ApiUser.image"]

        if current_thumbnail is None:
            # upload thumbnail
            self.sg.upload_thumbnail("ApiUser",
                                     d["created_by"]["id"],
                                     self._thumbnail_path)

            d = self.sg.find_one("Note",
                                 [["id", "is", note["id"]]],
                                 ["created_by", "created_by.ApiUser.image"])

            current_thumbnail = d["created_by.ApiUser.image"]

        # get thread
        result = self.sg.note_thread_read(note["id"])
        self.assertEqual(len(result), 1)
        self._check_note(result[0], note["id"], additional_fields=[])

        # now add a reply
        reply = self.sg.create("Reply", {"content": "Reply Content", "entity": note})

        # get thread
        result = self.sg.note_thread_read(note["id"])
        self.assertEqual(len(result), 2)

        # now check that the reply thumbnail field matches
        # the uploaded thumbnail. strip off any s3 querystring
        # for the comparison
        reply_thumb = result[1]["user"]["image"]
        url_obj_a = urllib.parse.urlparse(current_thumbnail)
        url_obj_b = urllib.parse.urlparse(reply_thumb)
        self.assertEqual("%s/%s" % (url_obj_a.netloc, url_obj_a.path),
                         "%s/%s" % (url_obj_b.netloc, url_obj_b.path),)

        # and check ther rest of the data
        self._check_note(result[0], note["id"], additional_fields=[])
        self._check_reply(result[1], reply["id"], additional_fields=[])

        # now upload an attachment
        attachment_id = self.sg.upload(note["type"], note["id"], self._thumbnail_path)

        # get thread
        result = self.sg.note_thread_read(note["id"])
        self.assertEqual(len(result), 3)
        self._check_note(result[0], note["id"], additional_fields=[])
        self._check_reply(result[1], reply["id"], additional_fields=[])
        self._check_attachment(result[2], attachment_id, additional_fields=[])

    # For now skip tests that are erroneously failling on some sites to
    # allow CI to pass until the known issue causing this is resolved.
    @base.skip("Skipping test that erroneously fails on some sites.")
    def test_complex(self):
        """
        Test note reply thread API call with additional params
        """
        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        additional_fields = {
            "Note": ["created_by.HumanUser.image",
                     "addressings_to",
                     "playlist",
                     "user"],
            "Reply": ["content"],
            "Attachment": ["this_file"]
        }

        # create note
        note = self.sg.create("Note", {"content": "Test!",
                                       "project": self.project,
                                       "addressings_to": [self.human_user]})

        # get thread
        result = self.sg.note_thread_read(note["id"], additional_fields)

        self.assertEqual(len(result), 1)
        self._check_note(result[0], note["id"], additional_fields["Note"])

        # now add a reply
        reply = self.sg.create("Reply", {"content": "Reply Content", "entity": note})

        # get thread
        result = self.sg.note_thread_read(note["id"], additional_fields)
        self.assertEqual(len(result), 2)
        self._check_note(result[0], note["id"], additional_fields["Note"])
        self._check_reply(result[1], reply["id"], additional_fields["Reply"])

        # now upload an attachment
        attachment_id = self.sg.upload(note["type"], note["id"], self._thumbnail_path)

        # get thread
        result = self.sg.note_thread_read(note["id"], additional_fields)
        self.assertEqual(len(result), 3)
        self._check_note(result[0], note["id"], additional_fields["Note"])
        self._check_reply(result[1], reply["id"], additional_fields["Reply"])

        self._check_attachment(result[2], attachment_id, additional_fields["Attachment"])


class TestTextSearch(base.LiveTestBase):
    """
    Unit tests for the text_search() method
    """

    def setUp(self):
        super(TestTextSearch, self).setUp()

        # create 5 shots and 5 assets to search for
        self._prefix = uuid.uuid4().hex

        batch_data = []
        for i in range(5):
            data = {"code": "%s Text Search %s" % (self._prefix, i),
                    "project": self.project}
            batch_data.append({"request_type": "create",
                               "entity_type": "Shot",
                               "data": data})
            batch_data.append({"request_type": "create",
                               "entity_type": "Asset",
                               "data": data})
        data = self.sg.batch(batch_data)

        self._shot_ids = [x["id"] for x in data if x["type"] == "Shot"]
        self._asset_ids = [x["id"] for x in data if x["type"] == "Asset"]

    def tearDown(self):

        # clean up
        batch_data = []
        for shot_id in self._shot_ids:
            batch_data.append({"request_type": "delete",
                               "entity_type": "Shot",
                               "entity_id": shot_id})
        for asset_id in self._asset_ids:
            batch_data.append({"request_type": "delete",
                               "entity_type": "Asset",
                               "entity_id": asset_id})
        self.sg.batch(batch_data)

        super(TestTextSearch, self).tearDown()

    def test_simple(self):
        """
        Test basic global search
        """
        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.text_search("%s Text Search" % self._prefix, {"Shot": []})

        self.assertEqual(set(["matches", "terms"]), set(result.keys()))
        self.assertEqual(result["terms"], [self._prefix, "text", "search"])
        matches = result["matches"]
        self.assertEqual(len(matches), 5)

        for match in matches:
            self.assertTrue(match["id"] in self._shot_ids)
            self.assertEqual(match["type"], "Shot")
            self.assertEqual(match["project_id"], self.project["id"])
            self.assertEqual(match["image"], None)

    def test_limit(self):
        """
        Test limited global search
        """
        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.text_search("%s Text Search" % self._prefix, {"Shot": []}, limit=3)
        matches = result["matches"]
        self.assertEqual(len(matches), 3)

    def test_entity_filter(self):
        """
        Test basic multi-type global search
        """
        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.text_search("%s Text Search" % self._prefix,
                                     {"Shot": [], "Asset": []})

        matches = result["matches"]

        self.assertEqual(set(["matches", "terms"]), set(result.keys()))
        self.assertEqual(len(matches), 10)

    def test_complex_entity_filter(self):
        """
        Test complex multi-type global search
        """
        if not self.sg.server_caps.version or self.sg.server_caps.version < (6, 2, 0):
            return

        result = self.sg.text_search("%s Text Search" % self._prefix,
                                     {
                                         "Shot": [["code", "ends_with", "3"]],
                                         "Asset": [{"filter_operator": "any",
                                                    "filters": [["code", "ends_with", "4"]]}]
                                     })

        matches = result["matches"]

        self.assertEqual(set(["matches", "terms"]), set(result.keys()))
        self.assertEqual(len(matches), 2)

        self.assertEqual(matches[0]["type"], "Shot")
        self.assertEqual(matches[0]["name"], "%s Text Search 3" % self._prefix)
        self.assertEqual(matches[1]["type"], "Asset")
        self.assertEqual(matches[1]["name"], "%s Text Search 4" % self._prefix)


class TestReadAdditionalFilterPresets(base.LiveTestBase):
    """
    Unit tests for the additional_filter_presets read parameter
    """

    def test_simple_case(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = [{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}]

        versions = self.sg.find("Version", filters, fields=fields, additional_filter_presets=additional_filters)
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version["id"], version["id"])

    def test_find_one(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = [{"preset_name": "LATEST", "latest_by": "ENTITIES_CREATED_AT"}]

        version = self.sg.find_one("Version", filters, fields=fields, additional_filter_presets=additional_filters)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version["id"], version["id"])

    def test_filter_with_no_name(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = [{}]

        self.assertRaises(shotgun_api3.Fault,
                          self.sg.find,
                          "Version", filters, fields=fields, additional_filter_presets=additional_filters)

    def test_invalid_filter(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = [{"preset_name": "BAD_FILTER"}]

        self.assertRaises(shotgun_api3.Fault,
                          self.sg.find,
                          "Version", filters, fields=fields, additional_filter_presets=additional_filters)

    def test_filter_not_iterable(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = 3

        self.assertRaises(shotgun_api3.Fault,
                          self.sg.find,
                          "Version", filters, fields=fields, additional_filter_presets=additional_filters)

    def test_filter_not_list_of_iterable(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = [3]

        self.assertRaises(shotgun_api3.Fault,
                          self.sg.find,
                          "Version", filters, fields=fields, additional_filter_presets=additional_filters)

    def test_multiple_latest_filters(self):
        if self.sg_version < (7, 0, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        filters = [
            ["project", "is", self.project],
            ["id", "is", self.version["id"]]
        ]

        fields = ["id"]

        additional_filters = ({"preset_name": "LATEST", "latest_by": "ENTITY_CREATED_AT"},
                              {"preset_name": "LATEST", "latest_by": "PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT"})

        self.assertRaises(shotgun_api3.Fault,
                          self.sg.find,
                          "Version", filters, fields=fields, additional_filter_presets=additional_filters)

    def test_modify_visibility(self):
        """
        Ensure the visibility of a field can be edited via the API.
        """
        # If the version of Shotgun is too old, do not run this test.
        # TODO: Update this with the real version number once the feature is released.
        if self.sg_version < (8, 5, 0):
            warnings.warn("Test bypassed because SG server used does not support this feature.", FutureWarning)
            return

        field_display_name = "Project Visibility Test"
        field_name = "sg_{0}".format(field_display_name.lower().replace(" ", "_"))

        schema = self.sg.schema_field_read("Asset")
        # Ensure the custom field exists.
        if field_name not in schema:
            self.sg.schema_field_create("Asset", "text", "Project Visibility Test")

        # Grab any two projects that we can use for toggling the visible property with.
        projects = self.sg.find("Project", [], order=[{"field_name": "id", "direction": "asc"}])
        project_1 = projects[0]
        project_2 = projects[1]

        # First, reset the field visibility in a known state, i.e. visible for both projects,
        # in case the last test run failed midway through.
        self.sg.schema_field_update("Asset", field_name, {"visible": True}, project_1)
        self.assertEqual(
            {"value": True, "editable": True},
            self.sg.schema_field_read("Asset", field_name, project_1)[field_name]["visible"]
        )
        self.sg.schema_field_update("Asset", field_name, {"visible": True}, project_2)
        self.assertEqual(
            {"value": True, "editable": True},
            self.sg.schema_field_read("Asset", field_name, project_2)[field_name]["visible"]
        )

        # Built-in fields should remain not editable.
        self.assertFalse(self.sg.schema_field_read("Asset", "code")["code"]["visible"]["editable"])

        # Custom fields should be editable
        self.assertEqual(
            {"value": True, "editable": True},
            self.sg.schema_field_read("Asset", field_name)[field_name]["visible"]
        )

        # Hide the field on project 1
        self.sg.schema_field_update("Asset", field_name, {"visible": False}, project_1)
        # It should not be visible anymore.
        self.assertEqual(
            {"value": False, "editable": True},
            self.sg.schema_field_read("Asset", field_name, project_1)[field_name]["visible"]
        )

        # The field should be visible on the second project.
        self.assertEqual(
            {"value": True, "editable": True},
            self.sg.schema_field_read("Asset", field_name, project_2)[field_name]["visible"]
        )

        # Restore the visibility on the field.
        self.sg.schema_field_update("Asset", field_name, {"visible": True}, project_1)
        self.assertEqual(
            {"value": True, "editable": True},
            self.sg.schema_field_read("Asset", field_name, project_1)[field_name]["visible"]
        )


class TestLibImports(base.LiveTestBase):
    """
    Ensure that included modules are importable and that the correct version is
    present.
    """

    def test_import_httplib(self):
        """
        Ensure that httplib2 is importable and objects are available

        This is important, because httplib2 imports switch between
        the Python 2 and 3 compatible versions, and the module imports are
        proxied to allow this.
        """
        from shotgun_api3.lib import httplib2
        # Ensure that Http object is available.  This is a good indication that
        # the httplib2 module contents are importable.
        self.assertTrue(hasattr(httplib2, "Http"))
        self.assertTrue(isinstance(httplib2.Http, object))

        # Ensure that the version of httplib2 compatible with the current Python
        # version was imported.
        # (The last module name for __module__ should be either python2 or
        # python3, depending on what has been imported.  Make sure we got the
        # right one.)
        httplib2_compat_version = httplib2.Http.__module__.split(".")[-1]
        if six.PY2:
            self.assertEqual(httplib2_compat_version, "python2")
        elif six.PY3:
            self.assertTrue(httplib2_compat_version, "python3")

        # Ensure that socks submodule is present and importable using a from
        # import -- this is a good indication that external httplib2 imports
        # from shotgun_api3 will work as expected.
        from shotgun_api3.lib.httplib2 import socks
        self.assertTrue(isinstance(socks, types.ModuleType))
        # Make sure that objects in socks are available as expected
        self.assertTrue(hasattr(socks, "HTTPError"))


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
