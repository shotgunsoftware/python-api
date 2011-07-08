"""Longer tests for calling the Shotgun API functions.

Includes the schema functions and the automated searching for all entity types
"""

import base, dummy_data

class TestShotgunApiLong(base.TestBase):
    
    def test_automated_find(self):
        """Called find for each entity type and read all fields"""
        
        #we just ned to get some response in the mock
        self._mock_http(
            {'results': {'entities': [{'id': -1, 'type': 'Mystery'}],
                 'paging_info': {'current_page': 1,
                                 'entities_per_page': 500,
                                 'entity_count': 1,
                                 'page_count': 1}}}
        )
        
        all_entities = self.sg.schema_entity_read().keys()
        direction = "asc"
        filter_operator = "all"
        limit = 1
        page = 1
        for entity_type in all_entities:
            if entity_type in ("Asset", "Task", "Shot", "Attachment"):
                continue
            print "Finding entity type", entity_type

            fields = self.sg.schema_field_read(entity_type)
            if not fields:
                print "No fields for %s skipping" % (entity_type,)
                continue
                 
            #trying to use some different code paths to the other find test
            order = [{'field_name': fields.keys()[0], 'direction': direction}]
            if "project" in fields:
                filters = [['project', 'is', self.project]]
            else:
                filters = []

            records = self.sg.find(entity_type, filters, fields=fields.keys(), 
                order=order, filter_operator=filter_operator, limit=limit, 
                page=page)
            
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
        return
        
    def test_schema(self):
        """Called schema functions"""
        
        self._mock_http(dummy_data.schema_entity_read)
        schema = self.sg.schema_entity_read()
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)

        self._mock_http(dummy_data.schema_read)
        schema = self.sg.schema_read()
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        
        self._mock_http(dummy_data.schema_field_read_version)
        schema = self.sg.schema_field_read("Version")
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        
        self._mock_http(dummy_data.schema_field_read_version_user)
        schema = self.sg.schema_field_read("Version", field_name="user")
        self.assertTrue(schema, dict)
        self.assertTrue(len(schema) > 0)
        self.assertTrue("user" in schema)
                
        self._mock_http({"results":"sg_monkeys"})
        properties = {
            "description" : "How many monkeys were needed"
        }
        new_field_name = self.sg.schema_field_create("Version", "number", 
            "Monkey Count", properties=properties)
           
        self._mock_http({"results":True})
        properties = {
            "description" : "How many monkeys turned up"
        }
        ret_val = self.sg.schema_field_update("Version", new_field_name, 
            properties)
        self.assertTrue(ret_val)
        
        self._mock_http({"results":True})
        ret_val = self.sg.schema_field_delete("Version", new_field_name)
        self.assertTrue(ret_val)
        
   
