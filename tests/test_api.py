"""Test calling the Shotgun API functions.

Includes short run tests, like simple crud and single finds. See 
test_api_long for other tests.
"""

import datetime
import os

import shotgun_api3 as api

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
        

    def test_get_session_token(self):
        """Got session UUID"""
        #TODO test results
        rv = self.sg._get_session_token()
        self.assertTrue(rv)
    

    def test_upload_download(self):
        """Upload and download a thumbnail"""
        #upload / download only works against a live server becuase it does 
        #not use the standard http interface
        if 'localhost' in self.server_url:
            print "upload / down tests skipped for localhost"
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


    def test_deprecated_functions(self):
        """Deprecated functions raise errors"""
        self.assertRaises(api.ShotgunError, self.sg.schema, "foo")
        self.assertRaises(api.ShotgunError, self.sg.entity_types)


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
        sg_ascii = api.Shotgun(self.config.server_url, 
                              self.config.script_name, 
                              self.config.api_key, 
                              ensure_ascii=True)

        result = sg_ascii.find_one('Note', [['id','is',self.note['id']]], fields=['content'])
        self.assertFalse(_has_unicode(result))


    def test_ensure_unicode(self):
        '''test_ensure_unicode tests ensure_unicode flag.'''
        sg_unicode = api.Shotgun(self.config.server_url, 
                              self.config.script_name, 
                              self.config.api_key, 
                              ensure_ascii=False)
        result = sg_unicode.find_one('Note', [['id','is',self.note['id']]], fields=['content'])
        print result
        self.assertTrue(_has_unicode(result))

def _has_unicode(data):
    for k, v in data.items():
        if (isinstance(k, unicode)):
            return True
        if (isinstance(v, unicode)):
            return True
    return False


