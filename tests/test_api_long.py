"""Longer tests for calling the Shotgun API functions.

Includes the schema functions and the automated searching for all entity types
"""

import base

class TestShotgunApiLong(base.LiveTestBase):
    
    def test_automated_find(self):
        """Called find for each entity type and read all fields"""
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
            #TODO for our test project, we haven't populated these entities....
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
                
        properties = { "description" : "How many monkeys were needed" }
        new_field_name = self.sg.schema_field_create("Version", "number", 
                                                     "Monkey Count", 
                                                     properties=properties)
           
        properties = {"description" : "How many monkeys turned up"}
        ret_val = self.sg.schema_field_update("Version",
                                               new_field_name, 
                                               properties)
        self.assertTrue(ret_val)
        
        ret_val = self.sg.schema_field_delete("Version", new_field_name)
        self.assertTrue(ret_val)
        
   
