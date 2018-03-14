"""Longer tests for calling the Shotgun API functions.

Includes the schema functions and the automated searching for all entity types
"""

import base
import random
import shotgun_api3
import os
import time

class TestShotgunApiLong(base.LiveTestBase):

    def test_automated_find(self):
        """Called find for each entity type and read all fields"""
        all_entities = self.sg.schema_entity_read().keys()
        direction = "asc"
        filter_operator = "all"
        limit = 1
        page = 1
        for entity_type in all_entities:
            if entity_type in ("Asset", "Task", "Shot", "Attachment",
                               "Candidate"):
                continue
            print "Finding entity type", entity_type

            fields = self.sg.schema_field_read(entity_type)
            if not fields:
                print "No fields for %s skipping" % (entity_type,)
                continue

            # trying to use some different code paths to the other find test
            # pivot_column fields aren't valid for sorting so ensure we're 
            # not using one.
            order_field = None
            for field_name, field in fields.iteritems():
                if field['data_type']["value"] != 'pivot_column':
                    order_field = field_name
                    break       
            # TODO for our test project, we haven't populated these entities....
            order = [{'field_name': order_field, 'direction': direction}]
            if "project" in fields:
                filters = [['project', 'is', self.project]]
            else:
                filters = []

            records = self.sg.find(entity_type, filters, fields=fields.keys(),
                                   order=order, filter_operator=filter_operator,
                                   limit=limit, page=page)

            self.assertTrue(isinstance(records, list))

            if filter_operator == "all":
                filter_operator = "any"
            else:
                filter_operator = "all"
            if direction == "desc":
                direction = "asc"
            else:
                direction = "desc"
            limit = (limit % 5) + 1
            page = (page % 3) + 1

    def test_schema(self):
        """Called schema functions"""

        schema = self.sg.schema_entity_read()
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)

        schema = self.sg.schema_read()
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)

        schema = self.sg.schema_field_read("Version")
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)

        schema = self.sg.schema_field_read("Version", field_name="user")
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        self.assertTrue("user" in schema)

        # An explanation is in order here. the field code that is created in shotgun is based on the human display name
        # that is provided , so for example "Money Count" would generate the field code 'sg_monkey_count' . The field
        # that is created in this test is retired at the end of the test but when this test is run again against 
        # the same database ( which happens on our Continuous Integration server ) trying to create a new field
        # called "Monkey Count" will now fail due to the new Delete Field Forever features we have added to shotgun
        # since there will a retired field called sg_monkey_count. The old behavior was to go ahead and create a new
        # "Monkey Count" field with a field code with an incremented number of the end like sg_monkey_count_1. The new
        # behavior is to raise an error in hopes the user will go into the UI and delete the old retired field forever.

        # make a the name of the field somewhat unique
        human_field_name = "Monkey " + str(random.getrandbits(24))
                
        properties = { "description" : "How many monkeys were needed" }
        new_field_name = self.sg.schema_field_create("Version", "number", human_field_name, 
                                                     properties=properties)

        properties = {"description": "How many monkeys turned up"}
        ret_val = self.sg.schema_field_update("Version",
                                              new_field_name,
                                              properties)
        self.assertTrue(ret_val)

        ret_val = self.sg.schema_field_delete("Version", new_field_name)
        self.assertTrue(ret_val)

    def test_schema_with_project(self):
        """Called schema functions with project"""

        project_entity = {'type': 'Project', 'id': 0}

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 4, 4):

            # server does not support this!
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_entity_read, project_entity)
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_read, project_entity)
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_field_read, 'Version', None, project_entity)
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_field_read, 'Version', 'user', project_entity)

        else:

            schema = self.sg.schema_entity_read(project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue('Project' in schema)
            self.assertTrue('visible' in schema['Project'])

            schema = self.sg.schema_read(project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue('Version' in schema)
            self.assertFalse('visible' in schema.keys())

            schema = self.sg.schema_field_read('Version', project_entity=project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue('user' in schema)
            self.assertTrue('visible' in schema['user'])

            schema = self.sg.schema_field_read('Version', 'user', project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue('user' in schema)
            self.assertTrue('visible' in schema['user'])

# Requires the Shotgun instance to have transcoding and 'transcoder_malware_support' enabled.
class TestMalwareScanning(base.LiveTestBase):

    def test_upload_version_pending_malware_pref_on(self):
        params = { 'project': {'type': 'Project', 'id': self.project['id']} }
        version_response = self.sg.create('Version', params, ['id'])
        version_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sg_logo.jpg')
        upload_response = self.sg.upload(
            'Version',
            version_response['id'],
            version_file,
            field_name='sg_uploaded_movie',
            display_name='Test Version')
        try:
            download_response = self.sg.download_attachment(upload_response)
            self.assertTrue(False, 'We should have raised a download error')
        except shotgun_api3.ShotgunFileDownloadError, e:
            # we want to be explicit with checking the response here
            lines = e.message.split('\n')
            self.assertEqual('HTTP Error 409: Conflict', lines[1])
            self.assertEqual('This file is undergoing a malware scan, please try again in a few minutes', lines[2])

    def test_upload_version_infected_malware_pref_on(self):
        params = { 'project': {'type': 'Project', 'id': self.project['id']} }
        version_response = self.sg.create('Version', params, ['id'])
        version_id = version_response['id']
        source_file = self.create_eicar_movie_file()
        upload_response = self.sg.upload(
            'Version',
            version_id,
            source_file,
            field_name='sg_uploaded_movie',
            display_name='Test Version')

        # we will check every 3 seconds for a change to the transcoding status, once it is no longer
        # active, we attempt to download the infected file
        start_transcoding_time = time.time()
        while  True:
            time.sleep(3)
            transcoding_status = self.sg.find_one('Version',
                filters=[["id", "is", version_id]],
                fields=['sg_uploaded_movie_transcoding_status'])
            if transcoding_status['sg_uploaded_movie_transcoding_status'] != 0:
                break

            # if we have waited to long, something is wrong, force the test to fail
            if (time.time() - start_transcoding_time > 60):
                os.remove(source_file)
                raise Exception('Waited too long for the transcoder to return')

        try:
            download_response = self.sg.download_attachment(upload_response)
            self.assertTrue(False, 'We should have raised a download error')
        except shotgun_api3.ShotgunFileDownloadError, e:
            lines = e.message.split('\n')
            self.assertEqual('HTTP Error 410: Gone', lines[1])
            self.assertEqual('File scanning has detected malware and the file has been quarantined', lines[2])

        os.remove(source_file)

    def create_eicar_movie_file(self):
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'eicar.mov')
        eicar_file = open(file_path, 'w')
        eicar_file.write("X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*\n")
        eicar_file.close()
        return file_path

if __name__ == '__main__':
    base.unittest.main()
