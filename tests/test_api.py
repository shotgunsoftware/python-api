"""Test calling the Shotgun API functions.

Includes short run tests, like simple crud and single finds. See
test_api_long for other tests.
"""

import datetime
import os
import re
from mock import patch, Mock, MagicMock
import unittest
import urlparse

import shotgun_api3
from shotgun_api3.lib.httplib2 import Http

import base

class TestShotgunApi(base.LiveTestBase):
    def setUp(self):
        super(TestShotgunApi, self).setUp()
        # give note unicode content
        self.sg.update('Note', self.note['id'], {'content':u'La Pe\xf1a'})

    def test_info(self):
        """Called info"""
        #TODO do more to check results
        self.sg.info()

    def test_server_dates(self):
        """Pass datetimes to the server"""
        #TODO check results
        t = { 'project': self.project,
              'start_date': datetime.date.today() }
        self.sg.create('Task', t, ['content', 'sg_status_list'])


    def test_batch(self):
        """Batched create, update, delete"""

        requests = [
        {
            "request_type" : "create",
            "entity_type" : "Shot",
            "data": {
                "code" : "New Shot 5",
                "project" : self.project
            }
        },
        {
            "request_type" : "update",
            "entity_type" : "Shot",
            "entity_id" : self.shot['id'],
            "data" : {
                "code" : "Changed 1"
            }
        }]

        new_shot, updated_shot = self.sg.batch(requests)

        self.assertEqual(self.shot['id'], updated_shot["id"])
        self.assertTrue(new_shot.get("id"))

        new_shot_id = new_shot["id"]
        requests = [{ "request_type" : "delete",
                      "entity_type"  : "Shot",
                      "entity_id"    : new_shot_id
                    },
                    {
                        "request_type" : "update",
                        "entity_type" : "Shot",
                        "entity_id" : self.shot['id'],
                        "data" : {
                            "code" : self.shot['code']
                            }
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
            'code':'JohnnyApple_Design01_FaceFinal',
            'description': 'fixed rig per director final notes',
            'sg_status_list':'rev',
            'entity': self.asset,
            'user': self.human_user
        }

        version = self.sg.create("Version", data, return_fields = ["id"])
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        #TODO check results more thoroughly
        #TODO: test returned fields are requested fields

        data = data = {
            "description" : "updated test"
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
        #TODO test results
        rv = self.sg._get_session_token()
        self.assertTrue(rv)

    def test_upload_download(self):
        """Upload and download an attachment tests"""
        # upload / download only works against a live server because it does
        # not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload / down tests skipped for localhost"
            return

        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
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
        attach_file = self.sg.download_attachment(ticket['attachments'][0])
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test download with attachment hash (write to disk)
        result = self.sg.download_attachment(ticket['attachments'][0],
                                             file_path=file_path)
        self.assertEqual(result, file_path)
        fp = open(file_path, 'rb')
        attach_file = fp.read()
        fp.close()
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        self.assertEqual(orig_file, attach_file)

        # test invalid requests
        INVALID_S3_URL = "https://sg-media-usor-01.s3.amazonaws.com/ada3de3ee3873875e1dd44f2eb0882c75ae36a4a/cd31346421dbeef781e0e480f259a3d36652d7f2/IMG_0465.MOV?AWSAccessKeyId=AKIAIQGOBSVN3FSQ5QFA&Expires=1371789959&Signature=SLbzv7DuVlZ8XAoOSQQAiGpF3u8%3D"
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
                            {"id":123, "type":"Shot"})
        self.assertRaises(TypeError, self.sg.download_attachment)

        # cleanup
        os.remove(file_path)

    def test_upload_thumbnail_in_create(self):
        """Upload a thumbnail via the create method"""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # test thumbnail upload
        data = {'image': path, 'code': 'Test Version',
                'project': self.project}
        new_version = self.sg.create("Version", data, return_fields=['image'])
        self.assertTrue(new_version is not None)
        self.assertTrue(isinstance(new_version, dict))
        self.assertTrue(isinstance(new_version.get('id'), int))
        self.assertEqual(new_version.get('type'), 'Version')
        self.assertEqual(new_version.get('project'), self.project)
        self.assertTrue(new_version.get('image') is not None)

        h = Http(".cache")
        thumb_resp, content = h.request(new_version.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

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

        h = Http(".cache")
        filmstrip_thumb_resp, content = h.request(new_version.get('filmstrip_image'), "GET")
        self.assertEqual(filmstrip_thumb_resp['status'], '200')
        self.assertEqual(filmstrip_thumb_resp['content-type'], 'image/jpeg')

        self.sg.delete("Version", new_version['id'])
    # end test_upload_thumbnail_in_create

    def test_upload_thumbnail_for_version(self):
        """simple upload thumbnail for version test."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Version",
            self.version['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        version_with_thumbnail = self.sg.find_one('Version',
            [['id', 'is', self.version['id']]],
            fields=['image'])

        self.assertEqual(version_with_thumbnail.get('type'), 'Version')
        self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])


        h = Http(".cache")
        thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image':None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_upload_thumbnail_for_task(self):
        """simple upload thumbnail for task test."""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Task",
            self.task['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        task_with_thumbnail = self.sg.find_one('Task',
            [['id', 'is', self.task['id']]],
            fields=['image'])

        self.assertEqual(task_with_thumbnail.get('type'), 'Task')
        self.assertEqual(task_with_thumbnail.get('id'), self.task['id'])

        h = Http(".cache")
        thumb_resp, content = h.request(task_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image': None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_linked_thumbnail_url(self):
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir, "sg_logo.jpg")))

        thumb_id = self.sg.upload_thumbnail("Project",
            self.version['project']['id'], path)

        response_version_with_project = self.sg.find(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'project.Project.image']
        )

        if self.sg.server_caps.version and self.sg.server_caps.version >= (3, 3, 0):

            self.assertEqual(response_version_with_project[0].get('type'), 'Version')
            self.assertEqual(response_version_with_project[0].get('id'), self.version['id'])
            self.assertEqual(response_version_with_project[0].get('code'), 'Sg unittest version')

            h = Http(".cache")
            thumb_resp, content = h.request(response_version_with_project[0].get('project.Project.image'), "GET")
            self.assertEqual(thumb_resp['status'], '200')
            self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        else:
            expected_version_with_project = [
                {
                    'code': 'Sg unittest version',
                    'type': 'Version',
                    'id': self.version['id'],
                    'project.Project.image': thumb_id
                }
            ]
            self.assertEqual(expected_version_with_project, response_version_with_project)

    def test_share_thumbnail(self):
        """share thumbnail between two entities"""
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))

        # upload thumbnail to first entity and share it with the rest
        thumbnail_id = self.sg.share_thumbnail(
            [self.version, self.shot],
            thumbnail_path=path)
        response_version_thumbnail = self.sg.find_one(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'image']
        )
        response_shot_thumbnail = self.sg.find_one(
            'Shot',
            [['id', 'is', self.shot['id']]],
            fields=['id', 'code', 'image']
        )

        shot_url = urlparse.urlparse(response_shot_thumbnail.get('image'))
        version_url = urlparse.urlparse(response_version_thumbnail.get('image'))
        shot_path = _get_path(shot_url)
        version_path = _get_path(version_url)
        self.assertEqual(shot_path, version_path)

        # share thumbnail from source entity with entities
        source_thumbnail_id = self.sg.upload_thumbnail("Version",
            self.version['id'], path)
        thumbnail_id = self.sg.share_thumbnail(
            [self.asset, self.shot],
            source_entity=self.version)
        response_version_thumbnail = self.sg.find_one(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'image']
        )
        response_shot_thumbnail = self.sg.find_one(
            'Shot',
            [['id', 'is', self.shot['id']]],
            fields=['id', 'code', 'image']
        )
        response_asset_thumbnail = self.sg.find_one(
            'Asset',
            [['id', 'is', self.asset['id']]],
            fields=['id', 'code', 'image']
        )

        shot_url = urlparse.urlparse(response_shot_thumbnail.get('image'))
        version_url = urlparse.urlparse(response_version_thumbnail.get('image'))
        asset_url = urlparse.urlparse(response_asset_thumbnail.get('image'))

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

    def test_deprecated_functions(self):
        """Deprecated functions raise errors"""
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema, "foo")
        self.assertRaises(shotgun_api3.ShotgunError, self.sg.entity_types)


    def test_simple_summary(self):
        '''test_simple_summary tests simple query using summarize.'''
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

    def test_summary_values(self):
        ''''''
        shot_data = {
            'sg_status_list': 'ip',
            'sg_cut_duration': 100,
            'project': self.project
        }
        shots = []
        shots.append(self.sg.create('Shot', dict(shot_data.items() +
                                    {'code': 'shot 1'}.items())))
        shots.append(self.sg.create('Shot', dict(shot_data.items() +
                                    {'code': 'shot 2'}.items())))
        shots.append(self.sg.create('Shot', dict(shot_data.items() +
                                    {'code': 'shot 3',
                                     'sg_status_list': 'fin'}.items())))
        summaries = [{'field': 'id', 'type': 'count'},
                     {'field': 'sg_cut_duration', 'type': 'sum'}]
        grouping = [{'direction': 'asc', 'field': 'sg_status_list', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summaries,
                                   grouping=grouping)
        count = {'id': 4, 'sg_cut_duration': 300}
        groups =[
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
            batch_data.append({"request_type": "delete",
                               "entity_type": "Shot",
                               "entity_id": s['id']
                              })
        self.sg.batch(batch_data)

        self.assertEqual(result['summaries'], count)
        self.assertEqual(result['groups'], groups)

    def test_ensure_ascii(self):
        '''test_ensure_ascii tests ensure_unicode flag.'''
        sg_ascii = shotgun_api3.Shotgun(self.config.server_url,
                              self.config.script_name,
                              self.config.api_key,
                              ensure_ascii=True)

        result = sg_ascii.find_one('Note', [['id','is',self.note['id']]], fields=['content'])
        self.assertFalse(_has_unicode(result))


    def test_ensure_unicode(self):
        '''test_ensure_unicode tests ensure_unicode flag.'''
        sg_unicode = shotgun_api3.Shotgun(self.config.server_url,
                              self.config.script_name,
                              self.config.api_key,
                              ensure_ascii=False)
        result = sg_unicode.find_one('Note', [['id','is',self.note['id']]], fields=['content'])
        self.assertTrue(_has_unicode(result))

    def test_work_schedule(self):
        '''test_work_schedule tests WorkDayRules api'''
        self.maxDiff = None

        start_date = '2012-01-01'
        start_date_obj = datetime.datetime(2012, 1, 1)
        end_date = '2012-01-07'
        end_date_obj = datetime.datetime(2012, 1, 7)

        project = self.project
        user = self.sg.find_one('HumanUser', [['projects', 'is', project]], ['name'])

        work_schedule = self.sg.work_schedule_read(start_date, end_date, project, user)

        self.assertRaises(shotgun_api3.ShotgunError, self.sg.work_schedule_read, start_date_obj, end_date_obj, project, user)

        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        self.assertEqual(work_schedule, resp)

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
        work_schedule['2012-01-03'] = {"reason": "PROJECT_EXCEPTION", "working": False, "description": "Project Holiday"}
        self.assertEqual(work_schedule, resp)

        jan4 = datetime.datetime(2012, 1, 4)

        self.assertRaises(shotgun_api3.ShotgunError, self.sg.work_schedule_update, jan4, False, 'Artist Holiday',  user=user)

        resp = self.sg.work_schedule_update("2012-01-04", False, 'Artist Holiday',  user=user)
        expected = {'date': '2012-01-04',
            'description': 'Artist Holiday',
            'project': None,
            'user': user,
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-04'] = {"reason": "USER_EXCEPTION", "working": False, "description": "Artist Holiday"}
        self.assertEqual(work_schedule, resp)

class TestDataTypes(base.LiveTestBase):
    '''Test fields representing the different data types mapped on the server side.

     Untested data types:  password, percent, pivot_column, serializable, image, currency
                           multi_entity, system_task_type, timecode, url, uuid, url_template
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
        pos_values = ['Internal','Client']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)


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
        pos_values = ['rdy','fin']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_status_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'sg_status_list'
        pos_values = ['rdy','fin']
        expected, actual = self.assert_set_field(entity,
                                                 entity_id,
                                                 field_name,
                                                 pos_values)
        self.assertEqual(expected, actual)

    def test_set_tag_list(self):
        entity = 'Task'
        entity_id = self.task['id']
        field_name = 'tag_list'
        pos_values = [['a','b'],['c']]
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

    def assert_set_field(self, entity, entity_id, field_name, pos_values):
        query_result = self.sg.find_one(entity,
                                         [['id', 'is', entity_id]],
                                         [field_name])
        initial_value = query_result[field_name]
        new_value = (initial_value == pos_values[0] and pos_values[1]) or pos_values[0]
        self.sg.update(entity, entity_id, {field_name:new_value})
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
        sg_utc= shotgun_api3.Shotgun(self.config.server_url,
                            self.config.script_name,
                            self.config.api_key,
                            http_proxy=self.config.http_proxy,
                            convert_datetimes_to_utc=True)
        self._assert_expected(sg_utc, self.datetime_none, self.datetime_local)
        self._assert_expected(sg_utc, self.datetime_local, self.datetime_local)

    def test_no_convert_to_utc(self):
        sg_no_utc= shotgun_api3.Shotgun(self.config.server_url,
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
        sg.update(entity_name, entity_id, {field_name:date_time})
        result = sg.find_one(entity_name, [['id','is',entity_id]],[field_name])
        self.assertEqual(result[field_name], expected)


class TestFind(base.LiveTestBase):
    def setUp(self):
        super(TestFind, self).setUp()
        # We will need the created_at field for the shot
        fields = self.shot.keys()[:]
        fields.append('created_at')
        self.shot = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]], fields)
        # We will need the uuid field for our LocalStorage
        fields = self.local_storage.keys()[:]
        fields.append('uuid')
        self.local_storage = self.sg.find_one('LocalStorage', [['id', 'is', self.local_storage['id']]], fields)

    def test_find(self):
        """Called find, find_one for known entities"""
        filters = []
        filters.append(['project','is', self.project])
        filters.append(['id','is', self.version['id']])

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
        # can't use 'any' in python 2.4
        for result in results:
            if result['id'] == expected_id:
                return True
        return False

    #TODO test all applicable data types for 'in'
        #'currency' => [BigDecimal, Float, NilClass],
        #'image' => [Hash, NilClass],
        #'percent' => [Bignum, Fixnum, NilClass],
        #'serializable' => [Hash, Array, NilClass],
        #'system_task_type' => [String, NilClass],
        #'timecode' => [Bignum, Fixnum, NilClass],
        #'footage' => [Bignum, Fixnum, NilClass, String, Float, BigDecimal],
        #'url' => [Hash, NilClass],

        #'uuid' => [String],

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

    #TODO add datetime test for in and not_in

    def test_in_relation_comma_duration(self):
        """
        Test that 'in' relation using commas (old format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = self.task.keys()[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task',[['id', 'is', self.task['id']]], new_task_keys)
        filters = [['duration', 'in', self.task['duration']],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_in_relation_list_duration(self):
        """
        Test that 'in' relation using list (new format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = self.task.keys()[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task',[['id', 'is', self.task['id']]], new_task_keys)
        filters = [['duration', 'in', [self.task['duration'],]],
                   ['project', 'is', self.project]]

        result = self._id_in_result('Task', filters, self.task['id'])
        self.assertTrue(result)

    def test_not_in_relation_duration(self):
        """
        Test that 'not_in' relation using commas (old format) works with duration fields.
        """
        # we need to get the duration value
        new_task_keys = self.task.keys()[:]
        new_task_keys.append('duration')
        self.task = self.sg.find_one('Task',[['id', 'is', self.task['id']]], new_task_keys)

        filters = [['duration', 'not_in', [self.task['duration'],]],
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
        filters = [['uuid', 'in', self.local_storage['uuid'],]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertTrue(result)

    def test_in_relation_list_uuid(self):
        """
        Test that 'in' relation using list (new format) works with uuid fields.
        """
        filters = [['uuid', 'in', [self.local_storage['uuid'],]]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertTrue(result)

    def test_not_in_relation_uuid(self):
        """
        Test that 'not_in' relation using commas (old format) works with uuid fields.
        """
        filters = [['uuid', 'not_in', [self.local_storage['uuid'],]]]

        result = self._id_in_result('LocalStorage', filters, self.local_storage['id'])
        self.assertFalse(result)

    def test_find(self):
        """Called find, find_one for known entities"""
        filters = []
        filters.append(['project','is', self.project])
        filters.append(['id','is', self.version['id']])

        fields = ['id']

        versions = self.sg.find("Version", filters, fields=fields)

        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])

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
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'Shot', [['image', 'is_not', [ {"type": "Thumbnail", "id": 9 }]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'HumanUser', [['password_proxy', 'is_not', [None]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'EventLogEntry', [['meta', 'is_not', [None]]])
        self.assertRaises(shotgun_api3.Fault, self.sg.find_one, 'Revision', [['meta', 'attachment', [None]]])

class TestFollow(base.LiveTestBase):
    def setUp(self):
        super(TestFollow, self).setUp()
        self.sg.update( 'HumanUser', self.human_user['id'], {'projects':[self.project]})

    def test_follow(self):
        '''Test follow method'''
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return

        result = self.sg.follow(self.human_user, self.shot)
        assert(result['followed'])

    def test_unfollow(self):
        '''Test unfollow method'''
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return
        
        result = self.sg.unfollow(self.human_user, self.shot)
        assert(result['unfollowed'])
    
    def test_followers(self):
        '''Test followers method'''
        
        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 1, 22):
            return
        
        result = self.sg.follow(self.human_user, self.shot)
        assert(result['followed'])
        
        result = self.sg.followers(self.shot)
        self.assertEqual( 1, len(result) )
        self.assertEqual( self.human_user['id'], result[0]['id'] )

class TestErrors(base.TestBase):
    def test_bad_auth(self):
        '''test_bad_auth invalid script name or api key raises fault'''
        server_url = self.config.server_url
        script_name = 'not_real_script_name'
        api_key = self.config.api_key
        login = self.config.human_login
        password = self.config.human_password

        # Test various combinations of illegal arguments
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, None, api_key)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, None)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, api_key, login=login, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, login=login)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, password=password)
        self.assertRaises(ValueError, shotgun_api3.Shotgun, server_url, script_name, login=login, password=password)

        # Test failed authentications
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

        script_name = self.config.script_name
        api_key = 'notrealapikey'
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

        sg = shotgun_api3.Shotgun(server_url, login=login, password='not a real password')
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

    @patch('shotgun_api3.shotgun.Http.request')
    def test_status_not_200(self, mock_request):
        response = MagicMock(name="response mock", spec=dict)
        response.status = 300
        response.reason = 'reason'
        mock_request.return_value = (response, {})
        self.assertRaises(shotgun_api3.ProtocolError, self.sg.find_one, 'Shot', [])

#    def test_malformed_response(self):
#        #TODO ResponseError
#        pass


class TestScriptUserSudoAuth(base.LiveTestBase):
    def setUp(self):
        super(TestScriptUserSudoAuth, self).setUp('ApiUser:Sudo')
    
    def test_user_is_creator(self):
        """
        Test 'sudo_as_login' option: on create, ensure appropriate user is set in created-by
        """
        data = {
            'project': self.project,
            'code':'JohnnyApple_Design01_FaceFinal',
            'description': 'fixed rig per director final notes',
            'sg_status_list':'na',
            'entity': self.asset,
            'user': self.human_user
        }

        version = self.sg.create("Version", data, return_fields = ["id","created_by"])
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        self.assertTrue("created_by" in version)
        self.assertEqual( self.config.human_name, version['created_by']['name'] )

class TestHumanUserSudoAuth(base.TestBase):
    def setUp(self):
        super(TestHumanUserSudoAuth, self).setUp('HumanUser:Sudo')
    
    def test_human_user_sudo_auth_fails(self):
        """
        Test 'sudo_as_login' option for HumanUser.
        Request fails on server because user has no permission to Sudo.
        """
        x = shotgun_api3.Shotgun(self.config.server_url,
                    login=self.config.human_login,
                    password=self.config.human_password,
                    http_proxy=self.config.http_proxy,
                    sudo_as_login="blah" )
        self.assertRaisesRegexp(shotgun_api3.Fault, "does not have permission to 'sudo'", x.find_one, 'Shot', [])


class TestHumanUserAuth(base.HumanUserAuthLiveTestBase):
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
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size

        # upload thumbnail
        thumb_id = self.sg.upload_thumbnail("Version",
            self.version['id'], path)
        self.assertTrue(isinstance(thumb_id, int))

        # check result on version
        version_with_thumbnail = self.sg.find_one('Version',
            [['id', 'is', self.version['id']]],
            fields=['image'])

        self.assertEqual(version_with_thumbnail.get('type'), 'Version')
        self.assertEqual(version_with_thumbnail.get('id'), self.version['id'])


        h = Http(".cache")
        thumb_resp, content = h.request(version_with_thumbnail.get('image'), "GET")
        self.assertEqual(thumb_resp['status'], '200')
        self.assertEqual(thumb_resp['content-type'], 'image/jpeg')

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image':None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)


def  _has_unicode(data):
    for k, v in data.items():
        if (isinstance(k, unicode)):
            return True
        if (isinstance(v, unicode)):
            return True
    return False

def _get_path(url):
    # url_parse returns native objects for older python versions (2.4)
    if isinstance(url, dict):
        return url.get('path')
    elif isinstance(url, tuple):
        return os.path.join(url[:4])
    else:
        return url.path

if __name__ == '__main__':
    unittest.main()
