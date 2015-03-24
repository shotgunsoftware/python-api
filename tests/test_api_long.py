"""Longer tests for calling the Shotgun API functions.

Includes the schema functions and the automated searching for all entity types
"""

import base
import random
import shotgun_api3

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
            # TODO for our test project, we haven't populated these entities....
            order = [{'field_name': fields.keys()[0], 'direction': direction}]
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
        """Called schema functions"""

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 4, 4):
            # server does not support this!
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_entity_read, {'type': 'Project', 'id': 0})
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_read, {'type': 'Project', 'id': 0})
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_field_read, 'Version', None, {'type': 'Project', 'id': 0})
            self.assertRaises(shotgun_api3.ShotgunError, self.sg.schema_field_read, 'Version', 'user', {'type': 'Project', 'id': 0})
            
        else:
            project_entity = {'type': 'Project', 'id': 0}
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


if __name__ == '__main__':
    base.unittest.main()
