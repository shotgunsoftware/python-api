"""Test calling the Shotgun API functions.

Includes short run tests, like simple crud and single finds. See 
test_api_long for other tests.
"""

import datetime
import os

import shotgun_api3 as api

import base

class TestShotgunApi(base.TestBase):
    

    def setUp(self):
        super(TestShotgunApi, self).setUp()
        
    def test_info(self):
        """Called info"""
        
        self._mock_http({
            'version': [2, 4, 0, u'Dev']
        })
        
        self.sg.info()
    
    def test_server_dates(self):
        """Pass datetimes to the server"""
        t = {
            'project': self.project,
            'start_date': datetime.date.today(),
        }
        self._mock_http({
            "results" : {
                "start_date" : "2011-04-27",
                "project" : {
                    "name" : "Demo Project",
                    "type" : "Project",
                    "id" : 4
                },
                "type" : "Task",
                "sg_status_list" : "wtg",
                "id" : 197,
                "content" : "New Task"
            }
        })
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
        
        self._mock_http({
            "results" : [ 
                {
                    "code" : "New Shot 5",
                    "project" : {
                        "name" : "Demo Project",
                        "type" : "Project",
                        "id" : 4
                    },
                    "type" : "Shot",
                    "id" : 870
                },
                {
                    "code" : "Changed 1", 
                    "type" : "Shot",
                    "id" : self.shot['id']
                }]
        })
        new_shot, updated_shot = self.sg.batch(requests)
        
        self.assertEqual(self.shot['id'], updated_shot["id"])
        self.assertTrue(new_shot.get("id"))
        
        new_shot_id = new_shot["id"]
        requests = [
        {
            "request_type" : "delete",
            "entity_type" : "Shot",
            "entity_id" : new_shot_id
        }]
        
        self._mock_http({"results" : [True]})
        result = self.sg.batch(requests)[0]
        self.assertEqual(True, result)
        return
        
    def test_create_update_delete(self):
        """Called create, update, delete, revive"""
        
        #Create
        self._mock_http(
            {'results': {'code': 'JohnnyApple_Design01_FaceFinal',
             'description': 'fixed rig per director final notes',
             'entity': {'id': 1, 'name': 'Asset 1', 'type': 'Asset'},
             'id': 3,
             'project': {'id': 1, 'name': 'Demo Project', 'type': 'Project'},
             'sg_status_list': 'rev',
             'type': 'Version',
             'user': {'id': 2, 'name': 'Aaron Morton', 'type': 'HumanUser'}}}
        )
        
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
        #TODO: test returned fields are requested fields
        
        #Update
        self._mock_http(
            {'results': {'description': 'updated test', 
                'id': version["id"], 'type': 'Version'}}
        )
        
        data = data = {
            "description" : "updated test"
        }
        version = self.sg.update("Version", version["id"], data)
        self.assertTrue(isinstance(version, dict))
        self.assertTrue("id" in version)
        
        #Delete
        self._mock_http(
            {'results': True}
        )
        rv = self.sg.delete("Version", version["id"])
        self.assertEqual(True, rv)
        self._mock_http(
            {'results': False}
        )
        rv = self.sg.delete("Version", version["id"])
        self.assertEqual(False, rv)

        #Revive
        self._mock_http(
            {'results': True}
        )
        rv = self.sg.revive("Version", version["id"])
        self.assertEqual(True, rv)
        self._mock_http(
            {'results': False}
        )
        rv = self.sg.revive("Version", version["id"])
        self.assertEqual(False, rv)
        
    def test_find(self):
        """Called find, find_one for known entities"""
        
        self._mock_http(
            {'results': {'entities': [self.version],
                 'paging_info': {'current_page': 1,
                                 'entities_per_page': 500,
                                 'entity_count': 1,
                                 'page_count': 1}}}
        )
        
        filters = [
            ['project','is', self.project],
            ['id','is', self.version['id']]
        ]
        
        fields = ['id']
        
        versions = self.sg.find("Version", filters, fields=fields)
        
        self.assertTrue(isinstance(versions, list))
        version = versions[0]
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])
        
        version = self.sg.find_one("Version", filters, fields=fields)
        self.assertEqual("Version", version["type"])
        self.assertEqual(self.version['id'], version["id"])
        
    def test_get_session_token(self):
        """Got session UUID"""
        
        uuid = "c6b57a9e207d13c74e6226eaba5eab77"
        self._mock_http(
            {"session_id" : uuid}
        )
        
        rv = self.sg._get_session_token()
        #we only know what the value is if we mocked the repsonse
        if self.is_mock:
            self.assertEqual(uuid, rv)
        self.assertTrue(rv)
        return
    
    def test_upload_download(self):
        """Upload and download a thumbnail"""
        
        #upload / download only works against a live server becuase it does 
        #not use the standard http interface
        if self.is_mock:
            print "upload / down tests skipped when mock enabled."
            return
        
        this_dir, _ = os.path.split(__file__)
        path = os.path.abspath(os.path.expanduser(
            os.path.join(this_dir,"sg_logo.jpg")))
        size = os.stat(path).st_size
        
        attach_id = self.sg.upload_thumbnail("Version", 
            self.version['id'], path, 
            tag_list="monkeys, everywhere, send, help")

        attach_id = self.sg.upload_thumbnail("Version", 
            self.version['id'], path, 
            tag_list="monkeys, everywhere, send, help")
            
        attach_file = self.sg.download_attachment(attach_id)
        self.assertTrue(attach_file is not None)
        self.assertEqual(size, len(attach_file))
        
        orig_file = open(path, "rb").read()
        self.assertEqual(orig_file, attach_file)
        return

    def test_deprecated_functions(self):
        """Deprecated functions raise errors"""
        self.assertRaises(api.ShotgunError, self.sg.schema, "foo")
        self.assertRaises(api.ShotgunError, self.sg.entity_types)

    def test_simple_summary(self):
        '''test_simple_summary tests simple query using summarize.'''
        summeries = [{'field': 'id', 'type': 'count'}]
        grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]
        self._mock_http({"results":{"groups":[{"group_name":"861",
                                               "summaries":{"id":1},
                                               "group_value":"861"},
                                               {"group_name":"888",
                                               "summaries":{"id":1},
                                               "group_value":"888"}],
                                    "summaries":{"id":11}
                                    }
                                }
                            )
        result = self.sg.summarize('Shot', 
                                   filters=filters, 
                                   summary_fields=summeries,
                                   grouping=grouping)
        assert(result['groups'])
        assert(result['groups'][0]['group_name'])
        assert(result['groups'][0]['group_value'])
        assert(result['groups'][0]['summaries'])
        assert(result['summaries'])

