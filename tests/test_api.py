"""Test calling the Shotgun API functions.

Includes short run tests, like simple crud and single finds. See
test_api_long for other tests.
"""

import datetime
import os
import re
from mock import patch, Mock, MagicMock
import unittest

import shotgun_api3
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
                    }]

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
        """Upload and download an attachment """
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

        attach_file = self.sg.download_attachment(attach_id)
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))

        orig_file = open(path, "rb").read()
        self.assertEqual(orig_file, attach_file)

    def test_upload_thumbnail_in_create(self):
        """Upload a thumbnail via the create method"""
        # upload / download only works against a live server because it does 
        # not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload via create tests skipped for localhost"
            return
        # end if
        
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
        self.assertTrue( re.match("http:\/\/%s\/files\/0000\/0000\/\d{4}/232/sg_logo.jpg.jpg" % (self.server_address), new_version.get('image')) )

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
        self.assertTrue( re.match("http:\/\/%s\/files\/0000\/0000\/\d{4}/sg_logo.jpg" % (self.server_address), new_version.get('filmstrip_image')) )
    # end test_upload_thumbnail_in_create

    def test_upload_thumbnail(self):
        # simple upload thumbnail test. 
        # upload / download only works against a live server because it does
        # not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload / down tests skipped for localhost"
            return

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
        expected_version_with_thumbnail = {
            'image': 'http://%s/files/0000/0000/%04d/232/sg_logo.jpg.jpg' % (self.server_address, thumb_id),
            'type': 'Version',
            'id': self.version['id']
        }
        self.assertEqual(expected_version_with_thumbnail, version_with_thumbnail)

        # clear thumbnail
        response_clear_thumbnail = self.sg.update("Version",
            self.version['id'], {'image':None})
        expected_clear_thumbnail = {'id': self.version['id'], 'image': None, 'type': 'Version'}
        self.assertEqual(expected_clear_thumbnail, response_clear_thumbnail)

    def test_linked_thumbnail_url(self):
        #upload / download only works against a live server because it does 
        #not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload / down tests skipped for localhost"
            return

        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))

        thumb_id = self.sg.upload_thumbnail("Project",
            self.version['project']['id'], path)

        response_version_with_project = self.sg.find(
            'Version',
            [['id', 'is', self.version['id']]],
            fields=['id', 'code', 'project.Project.image']
        )

        if self.sg.server_caps.version and self.sg.server_caps.version >= (3, 3, 0):
            expected_version_with_project = [
                {
                    'code': 'Sg unittest version',
                    'type': 'Version',
                    'id': self.version['id'],
                    'project.Project.image': 'http://%s/files/0000/0000/%04d/232/sg_logo.jpg.jpg' % (self.server_address, thumb_id)
                }
            ]
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
        # upload / download only works against a live server because it does 
        # not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload / down tests skipped for localhost"
            return

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
        self.assertEqual(response_shot_thumbnail.get('image'), 
                         response_version_thumbnail.get('image'))

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
        self.assertEqual(response_version_thumbnail.get('image'), 
                         response_shot_thumbnail.get('image'))
        self.assertEqual(response_version_thumbnail.get('image'), 
                         response_asset_thumbnail.get('image'))

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
        summeries = [{'field': 'id', 'type': 'count'}]
        grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summeries,
                                   grouping=grouping)
        assert(result['groups'])
        assert(result['groups'][0]['group_name'])
        assert(result['groups'][0]['group_value'])
        assert(result['groups'][0]['summaries'])
        assert(result['summaries'])

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

        project = self.sg.find_one('Project', [])
        user = self.sg.find_one('HumanUser', [['projects', 'is', project]])

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
            'project': {'id': 4, 'name': 'Demo Project', 'type': 'Project'},
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
            'user': {'id': 12, 'name': 'Artist 8', 'type': 'HumanUser'},
            'working': False
        }
        self.assertEqual(expected, resp)
        resp = self.sg.work_schedule_read(start_date, end_date, project, user)
        work_schedule['2012-01-04'] = {"reason": "USER_EXCEPTION", "working": False, "description": "Artist Holiday"}
        self.assertEqual(work_schedule, resp)

class TestDataTypes(base.LiveTestBase):
    '''Test fields representing the different data types mapped on the server side.

     Untested data types:  password, percent, pivot_column, serializable, image, currency
                           multi_entity, system_task_type, timecode, url, uuid
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
        field_name = 'read_by_current_user'
        pos_values = ['read','unread']
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


class TestErrors(base.TestBase):
    def test_bad_auth(self):
        '''test_bad_auth invalid script name or api key raises fault'''
        server_url = self.config.server_url
        script_name = 'not_real_script_name'
        api_key = self.config.api_key
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
        self.assertRaises(shotgun_api3.Fault, sg.find_one, 'Shot',[])

        script_name = self.config.script_name
        api_key = 'notrealapikey'
        sg = shotgun_api3.Shotgun(server_url, script_name, api_key)
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


def  _has_unicode(data):
    for k, v in data.items():
        if (isinstance(k, unicode)):
            return True
        if (isinstance(v, unicode)):
            return True
    return False


if __name__ == '__main__':
    unittest.main()
