# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""Longer tests for calling the Shotgun API functions.

Includes the schema functions and the automated searching for all entity types
"""

from __future__ import print_function
from . import base
import random
import shotgun_api3
from shotgun_api3.lib import six


class TestShotgunApiLong(base.LiveTestBase):
    def test_automated_find(self):
        """Called find for each entity type and read all fields"""

        # Whitelist certain data types for order_field, since no_sorting is not
        # currently exposed.  These should be good bets to be sortable.
        sortable_types = ("number", "date")

        all_entities = list(self.sg.schema_entity_read().keys())
        direction = "asc"
        filter_operator = "all"
        limit = 1
        page = 1
        for entity_type in all_entities:
            if entity_type in (
                "Asset",
                "Task",
                "Shot",
                "Attachment",
                "Candidate",
                "MimProject",
                "MimEntity",
                "MimField",
            ):
                continue
            print("Finding entity type %s" % entity_type)

            fields = self.sg.schema_field_read(entity_type)
            if not fields:
                print("No fields for %s skipping" % entity_type)
                continue

            # trying to use some different code paths to the other find test
            # pivot_column fields aren't valid for sorting so ensure we're
            # not using one.
            order_field = None
            for field_name, field in six.iteritems(fields):
                # Restrict sorting to only types we know will always be sortable
                # Since no_sorting is not exposed to us, we'll have to rely on
                # this as a safeguard against trying to sort by a field with
                # allow_sorting=false.
                if field["data_type"]["value"] in sortable_types:
                    order_field = field_name
                    break
            # TODO for our test project, we haven't populated these entities....
            order = None
            if order_field:
                order = [{"field_name": order_field, "direction": direction}]
            if "project" in fields:
                filters = [["project", "is", self.project]]
            else:
                filters = []

            records = self.sg.find(
                entity_type,
                filters,
                fields=list(fields.keys()),
                order=order,
                filter_operator=filter_operator,
                limit=limit,
                page=page,
            )

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

    @base.skip("Skipping test due to CI failure. Too many database columns.")
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

        properties = {"description": "How many monkeys were needed"}
        new_field_name = self.sg.schema_field_create(
            "Version", "number", human_field_name, properties=properties
        )

        properties = {"description": "How many monkeys turned up"}
        ret_val = self.sg.schema_field_update("Version", new_field_name, properties)
        self.assertTrue(ret_val)

        ret_val = self.sg.schema_field_delete("Version", new_field_name)
        self.assertTrue(ret_val)

    def test_schema_with_project(self):
        """Called schema functions with project"""

        project_entity = {"type": "Project", "id": 0}

        if not self.sg.server_caps.version or self.sg.server_caps.version < (5, 4, 4):
            # server does not support this!
            self.assertRaises(
                shotgun_api3.ShotgunError, self.sg.schema_entity_read, project_entity
            )
            self.assertRaises(
                shotgun_api3.ShotgunError, self.sg.schema_read, project_entity
            )
            self.assertRaises(
                shotgun_api3.ShotgunError,
                self.sg.schema_field_read,
                "Version",
                None,
                project_entity,
            )
            self.assertRaises(
                shotgun_api3.ShotgunError,
                self.sg.schema_field_read,
                "Version",
                "user",
                project_entity,
            )

        else:
            schema = self.sg.schema_entity_read(project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue("Project" in schema)
            self.assertTrue("visible" in schema["Project"])

            schema = self.sg.schema_read(project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue("Version" in schema)
            self.assertFalse("visible" in schema)

            schema = self.sg.schema_field_read("Version", project_entity=project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue("user" in schema)
            self.assertTrue("visible" in schema["user"])

            schema = self.sg.schema_field_read("Version", "user", project_entity)
            self.assertTrue(schema, dict)
            self.assertTrue(len(schema) > 0)
            self.assertTrue("user" in schema)
            self.assertTrue("visible" in schema["user"])


if __name__ == "__main__":
    base.unittest.main()
