#! /opt/local/bin/python

#  -----------------------------------------------------------------------------
#  Copyright (c) 2009-2017, Shotgun Software Inc
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#   - Redistributions of source code must retain the above copyright notice, this
#     list of conditions and the following disclaimer.
#
#   - Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#
#   - Neither the name of the Shotgun Software Inc nor the names of its
#     contributors may be used to endorse or promote products derived from this
#     software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#  FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------

"""
Unit tests for Mockgun. Does not require an Internet connection
and can be run on their own by typing "python test_mockgun.py".
"""

import re
import os
import unittest
from shotgun_api3.lib.mockgun import Shotgun as Mockgun
from shotgun_api3 import ShotgunError


mockgun_schema_folder = os.path.join(
    os.path.dirname(__file__),
    "mockgun"
)

Mockgun.set_schema_paths(
    os.path.join(mockgun_schema_folder, "schema.pickle"),
    os.path.join(mockgun_schema_folder, "schema_entity.pickle")
)


# FIXME: This should probably be refactored into a base class for
# all test bases
class TestBaseWithExceptionTests(unittest.TestCase):
    """
    Implements a Python 2.4 compatible assertRaisesRegexp like method. This
    was introduced in Python 2.7.
    """
    def assertRaisesRegexp(self, exception_type, re_msg, func):
        try:
            func()
        except exception_type, exception:
            matches = re.findall(re_msg, str(exception))
            if not matches:
                self.fail("Expected exception to match '%s', got '%s' instead." % (
                    re_msg, str(exception)
                ))
        except Exception, ex:
            self.fail("Expected exception of type %s, got %s" % (exception_type, type(ex)))
        else:
            self.fail("Expected %s was not raised." % exception_type)


class TestMockgunModuleInterface(unittest.TestCase):
    """
    mockgun.py was turned into a module. Ensure we haven't broken the interface.
    """

    def test_interface_intact(self):
        """
        Ensure everything that was public before still is.
        """

        from shotgun_api3.lib import mockgun
        # Try to access everything. If something is missing, it will raise an
        # error.
        mockgun.MockgunError
        mockgun.generate_schema
        mockgun.Shotgun


class TestValidateFilterSyntax(TestBaseWithExceptionTests):
    """
    Tests filter syntax support.
    """

    def setUp(self):
        """
        Creates test data.
        """
        super(TestValidateFilterSyntax, self).setUp()

        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        self._mockgun.create("Shot", {"code": "shot"})

    def test_filter_array_or_dict(self):
        """
        Ensure that arrays and dictionaries are supported for filters.
        """
        # This should not throw.
        self._mockgun.find(
            "Shot",
            [
                {
                    "filter_operator": "any",
                    "filters": [["code", "is", "shot"]]
                },
                [
                    "code", "is", "shot"
                ]
            ]
        )

        # We can't have not dict/list values for filters however.
        self.assertRaisesRegexp(
            ShotgunError,
            "Filters can only be lists or dictionaries, not int.",
            lambda: self._mockgun.find(
                "Shot",
                [1]
            )
        )


class TestEntityFieldComparison(TestBaseWithExceptionTests):
    """
    Checks if entity fields comparison work.
    """

    def setUp(self):
        """
        Creates test data.
        """
        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        self._project_link = self._mockgun.create("Project", {"name": "project"})

        # This entity will ensure that a populated link field will be comparable.
        self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_project", "project": self._project_link}
        )

        # This entity will ensure that an unpopulated link field will be comparable.
        self._mockgun.create("PipelineConfiguration", {"code": "without_project"})

    def test_searching_for_none_entity_field(self):
        """
        Ensures that comparison with None work.
        """

        items = self._mockgun.find("PipelineConfiguration", [["project", "is", None]])
        self.assertEqual(len(items), 1)

        items = self._mockgun.find("PipelineConfiguration", [["project", "is_not", None]])
        self.assertEqual(len(items), 1)

    def test_searching_for_initialized_entity_field(self):
        """
        Ensures that comparison with an entity works.
        """
        items = self._mockgun.find("PipelineConfiguration", [["project", "is", self._project_link]])
        self.assertEqual(len(items), 1)

        items = self._mockgun.find("PipelineConfiguration", [["project", "is_not", self._project_link]])
        self.assertEqual(len(items), 1)


class TestTextFieldOperators(TestBaseWithExceptionTests):
    """
    Checks if text field comparison work.
    """
    def setUp(self):
        """
        Creates test data.
        """
        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")
        self._user = self._mockgun.create("HumanUser", {"login": "user"})

    def test_operator_contains(self):
        """
        Ensures contains operator works.
        """
        item = self._mockgun.find_one("HumanUser", [["login", "contains", "se"]])
        self.assertTrue(item)


class TestMultiEntityFieldComparison(TestBaseWithExceptionTests):
    """
    Ensures multi entity field comparison work.
    """

    def setUp(self):
        """
        Creates test data.
        """

        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        # Create two users to assign to the pipeline configurations.
        self._user1 = self._mockgun.create("HumanUser", {"login": "user1"})
        self._user2 = self._mockgun.create("HumanUser", {"login": "user2"})

        # Create a project for nested sub entity field
        self._project1 = self._mockgun.create("Project", {"name": "project1", "users": [self._user1]})
        self._project2 = self._mockgun.create("Project", {"name": "project2", "users": [self._user2]})
        
        self._sequence1 = self._mockgun.create("Sequence", {"code":"01", "project":self._project1})
        self._shot1 = self._mockgun.create("Shot", {"code":"01_0010", "project":self._project1, "sg_sequence": self._sequence1})
        
        self._task_seq = self._mockgun.create("Task", {"entity": self._sequence1})
        self._task_shot = self._mockgun.create("Task", {"entity": self._shot1})

        # Create pipeline configurations that are assigned none, one or two users.
        self._pipeline_config_1 = self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_user1", "users": [self._user1], "project": self._project1}
        )

        self._pipeline_config_2 = self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_user2", "users": [self._user2], "project": self._project2}
        )

        self._pipeline_config_3 = self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_both", "users": [self._user2, self._user1]}
        )

        self._pipeline_config_4 = self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_none", "users": []}
        )

    def test_find_by_sub_entity_field(self):
        """
        Ensures that queries on linked entity fields works.
        """
        items = self._mockgun.find("PipelineConfiguration", [["users.HumanUser.login", "is", "user1"]])
        self.assertEqual(len(items), 2)

        items = self._mockgun.find("PipelineConfiguration", [["users.HumanUser.login", "is", "user2"]])
        self.assertEqual(len(items), 2)

        items = self._mockgun.find("PipelineConfiguration", [["users.HumanUser.login", "contains", "ser"]])
        self.assertEqual(len(items), 3)

        # Lets get fancy a bit.
        items = self._mockgun.find("PipelineConfiguration", [{
            "filter_operator": "any",
            "filters": [
                ["users.HumanUser.login", "is", "user1"],
                ["users.HumanUser.login", "is", "user2"]
            ]}]
        )
        self.assertEqual(len(items), 3)

        items = self._mockgun.find("PipelineConfiguration", [{
            "filter_operator": "all",
            "filters": [
                ["users.HumanUser.login", "is", "user1"],
                ["users.HumanUser.login", "is", "user2"]
            ]}]
        )
        self.assertEqual(len(items), 1)
        
        # Try with multi entities
        item = self._mockgun.find_one("Task", [
            ['entity.Shot.code', 'is', self._shot1['code']]
        ])
        self.assertNotEqual(None, item)
        self.assertEqual(self._task_shot["id"], item["id"])
        
        item = self._mockgun.find_one("Task", [
            ['entity.Sequence.code', 'is', self._sequence1['code']]
        ])
        self.assertNotEqual(None, item)
        self.assertEqual(self._task_seq["id"], item["id"])

    def test_find_by_sub_entity_field_nested(self):
        """
        Ensure that queries on nested linked entity fields work.
        """
        items = self._mockgun.find("PipelineConfiguration", [
            ["project.Project.users.HumanUser.login", "is", "user1"]
        ])
        self.assertEqual(len(items), 1)
        self.assertEqual(self._pipeline_config_1['id'], items[0]['id'])

        items = self._mockgun.find("PipelineConfiguration", [
            ["project.Project.users.HumanUser.login", "is", "user2"]
        ])
        self.assertEqual(len(items), 1)
        self.assertEqual(self._pipeline_config_2['id'], items[0]['id'])
        
    def test_find_with_none(self):
        """
        Ensures comparison with multi-entity fields and None works.
        """
        items = self._mockgun.find("PipelineConfiguration", [["users", "is", None]], ["users"])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["users"], [])

        items = self._mockgun.find("PipelineConfiguration", [["users", "is_not", None]], ["users"])
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertTrue(len(item["users"]) > 0)


class TestFindFields(TestBaseWithExceptionTests):
    """
    Ensure that using the 'field' argument in the find method work.
    """

    def setUp(self):
        """Creates test data."""
        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        # Create two users to assign to the pipeline configurations.
        self._user1 = self._mockgun.create("HumanUser", {"login": "user1", "firstname": "firstname1"})

        # Create a project for nested sub entity field
        self._project1 = self._mockgun.create("Project", {"name": "project1", "users": [self._user1]})

        # Create pipeline configurations that are assigned none, one or two users.
        self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_user1", "users": [self._user1], "project": self._project1}
        )

    def test_field(self):
        item = self._mockgun.find_one("HumanUser", [
            ["login", "is", "user1"]
        ], ["firstname"])
        self.assertIn("firstname",item)
        self.assertEqual("firstname1", item["firstname"])

    def test_find_field_multi_entity(self):
        item = self._mockgun.find_one("PipelineConfiguration", [
            ["project.Project.users.HumanUser.login", "is", "user1"]
        ], ["project.Project.name"])
        self.assertIn("project.Project.name", item)
        self.assertEqual("project1", item["project.Project.name"])


class TestFindOrder(TestBaseWithExceptionTests):
    """
    Ensure that using the 'order' argument in the find method work.
    """
    def setUp(self):
        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        # Create two users to assign to the pipeline configurations.
        self._user1 = self._mockgun.create("HumanUser", {"login": "user1", "firstname": "firstname1", "email": "user1@foobar.com"})
        self._user2 = self._mockgun.create("HumanUser", {"login": "user2", "firstname": "firstname2", "email": "user2@foobar.com"})

        # Create a project for nested sub entity field
        self._project1 = self._mockgun.create("Project", {"name": "project1", "users": [self._user1]})
        self._project2 = self._mockgun.create("Project", {"name": "project2", "users": [self._user2]})

        # Create two PipelineConfiguration entities so we can test multi-entity sorting.
        self._pipeline_configutation_1 = self._mockgun.create("PipelineConfiguration", {
            "code": "PipelineConfiguration1", "users": [self._user2], "project": self._project1})
        self._pipeline_configutation_2 = self._mockgun.create("PipelineConfiguration", {
            "code": "PipelineConfiguration2", "users": [self._user1], "project": self._project2})

    def test_find_order(self):
        # Test ascending order
        item = self._mockgun.find_one("HumanUser", [], order=[{'field_name': 'login', 'direction': 'asc'}])
        self.assertEqual(self._user1['id'], item['id'])

        # Test descending order
        item = self._mockgun.find_one("HumanUser", [], order=[{'field_name': 'login', 'direction': 'desc'}])
        self.assertEqual(self._user2['id'], item['id'])

    def test_find_order_linked_entity_field(self):
        """Ensure we are able to sort data using a linked entity field."""
        # Test ascending order
        item = self._mockgun.find_one("PipelineConfiguration", [], order=[{'field_name': 'project.Project.name', 'direction': 'asc'}])
        self.assertEqual(self._pipeline_configutation_1['id'], item['id'])

        # Test descending order
        item = self._mockgun.find_one("PipelineConfiguration", [], order=[{'field_name': 'project.Project.name', 'direction': 'desc'}])
        self.assertEqual(self._pipeline_configutation_2['id'], item['id'])

    def test_find_order_fields_leak(self):
        """Ensure that additional fields passed through the order argument but NOT via the field argument are not added to the resulting fields."""
        item = self._mockgun.find_one("HumanUser", [], fields=['email'], order=[{'field_name': 'login', 'direction': 'asc'}])
        self.assertEqual(set(item.keys()), set(['id', 'type', 'email']))  # note: we don't verify the order yet

    def test_find_order_date_created(self):
        """Ensure we are able to sort entities by their creation date."""
        item = self._mockgun.find_one("PipelineConfiguration", [], order=[{'field_name': 'created_at', 'direction': 'asc'}])
        self.assertEqual(self._pipeline_configutation_1['id'], item['id'])

        item = self._mockgun.find_one("PipelineConfiguration", [], order=[{'field_name': 'created_at', 'direction': 'desc'}])
        self.assertEqual(self._pipeline_configutation_2['id'], item['id'])


class TestFilterOperator(TestBaseWithExceptionTests):
    """
    Unit tests for the filter_operator filter syntax.
    """

    def setUp(self):
        """
        Creates tests data.
        """
        super(TestFilterOperator, self).setUp()

        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        self._prj1_link = self._mockgun.create(
            "Project",
            {
                "name": "prj1"
            }
        )

        self._prj2_link = self._mockgun.create(
            "Project",
            {
                "name": "prj2"
            }
        )

        self._shot1 = self._mockgun.create(
            "Shot",
            {
                "code": "shot1",
                "project": self._prj1_link
            }
        )

        self._shot2 = self._mockgun.create(
            "Shot",
            {
                "code": "shot2",
                "project": self._prj1_link
            }
        )

        self._shot3 = self._mockgun.create(
            "Shot",
            {
                "code": "shot3",
                "project": self._prj2_link
            }
        )

    def test_simple_filter_operators(self):
        """
        Tests a simple use of the filter_operator.
        """
        shots = self._mockgun.find(
            "Shot",
            [{
                "filter_operator": "any",
                "filters": [
                    ["code", "is", "shot1"],
                    ["code", "is", "shot2"]
                ]
            }]
        )

        self.assertEqual(len(shots), 2)

        shots = self._mockgun.find(
            "Shot",
            [{
                "filter_operator": "all",
                "filters": [
                    ["code", "is", "shot1"],
                    ["code", "is", "shot2"]
                ]
            }]
        )

        self.assertEqual(len(shots), 0)

    def test_nested_filter_operators(self):
        """
        Tests a the use of the filter_operator nested
        inside the filter_operator.
        """
        shots = self._mockgun.find(
            "Shot",
            [
                {
                    "filter_operator": "any",
                    "filters": [
                        {
                            "filter_operator": "all",
                            "filters": [
                                ["code", "is", "shot1"],
                                ["project", "is", self._prj1_link]
                            ]
                        },
                        {
                            "filter_operator": "all",
                            "filters": [
                                ["code", "is", "shot3"],
                                ["project", "is", self._prj2_link]
                            ]
                        }
                    ]
                }
            ]
        )

        self.assertEqual(len(shots), 2)

    def test_invalid_operator(self):

        self.assertRaisesRegexp(
            ShotgunError,
            "Unknown filter_operator type: bad",
            lambda: self._mockgun.find(
                "Shot",
                [
                    {
                        "filter_operator": "bad",
                        "filters": []
                    }
                ])
        )

        self.assertRaisesRegexp(
            ShotgunError,
            "Bad filter operator, requires keys 'filter_operator' and 'filters',",
            lambda: self._mockgun.find(
                "Shot",
                [
                    {
                    }
                ])
        )


if __name__ == '__main__':
    unittest.main()
