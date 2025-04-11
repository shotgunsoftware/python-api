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

import datetime
import re
import os
import unittest
from shotgun_api3.lib.mockgun import Shotgun as Mockgun
from shotgun_api3 import ShotgunError


mockgun_schema_folder = os.path.join(os.path.dirname(__file__), "mockgun")

Mockgun.set_schema_paths(
    os.path.join(mockgun_schema_folder, "schema.pickle"),
    os.path.join(mockgun_schema_folder, "schema_entity.pickle"),
)


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


class TestValidateFilterSyntax(unittest.TestCase):
    """
    Tests filter syntax support.
    """

    def setUp(self):
        """
        Creates test data.
        """
        super(TestValidateFilterSyntax, self).setUp()

        self._mockgun = Mockgun(
            "https://test.shotgunstudio.com", login="user", password="1234"
        )

        self._mockgun.create("Shot", {"code": "shot"})

    def test_filter_array_or_dict(self):
        """
        Ensure that arrays and dictionaries are supported for filters.
        """
        # This should not throw.
        self._mockgun.find(
            "Shot",
            [
                {"filter_operator": "any", "filters": [["code", "is", "shot"]]},
                ["code", "is", "shot"],
            ],
        )

        # We can't have not dict/list values for filters however.
        self.assertRaisesRegex(
            ShotgunError,
            "Filters can only be lists or dictionaries, not int.",
            lambda: self._mockgun.find("Shot", [1]),
        )


class TestEntityFieldComparison(unittest.TestCase):
    """
    Checks if entity fields comparison work.
    """

    def setUp(self):
        """
        Creates test data.
        """
        self._mockgun = Mockgun(
            "https://test.shotgunstudio.com", login="user", password="1234"
        )

        self._project_link = self._mockgun.create(
            "Project", {"name": "project", "archived": False}
        )

        # This entity will ensure that a populated link field will be comparable.
        self._mockgun.create(
            "PipelineConfiguration",
            {
                "code": "with_project",
                "project": self._project_link,
            },
        )

        # This entity will ensure that an unpopulated link field will be comparable.
        self._mockgun.create("PipelineConfiguration", {"code": "without_project"})

    def test_searching_for_none_entity_field(self):
        """
        Ensures that comparison with None work.
        """

        items = self._mockgun.find("PipelineConfiguration", [["project", "is", None]])
        self.assertEqual(len(items), 1)

        items = self._mockgun.find(
            "PipelineConfiguration", [["project", "is_not", None]]
        )
        self.assertEqual(len(items), 1)

    def test_searching_for_initialized_entity_field(self):
        """
        Ensures that comparison with an entity works.
        """
        items = self._mockgun.find(
            "PipelineConfiguration", [["project", "is", self._project_link]]
        )
        self.assertEqual(len(items), 1)

        items = self._mockgun.find(
            "PipelineConfiguration", [["project", "is_not", self._project_link]]
        )
        self.assertEqual(len(items), 1)

    def test_find_entity_with_none_link(self):
        """
        Make sure that we can search for sub entity fields on entities that have the field not set.
        """
        # The pipeline configuration without_project doesn't have the project field set, so we're expecting
        # it to not be returned here.
        items = self._mockgun.find(
            "PipelineConfiguration", [["project.Project.archived", "is", False]]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self._project_link["id"])


class TestTextFieldOperators(unittest.TestCase):
    """
    Checks if text field comparison work.
    """

    def setUp(self):
        """
        Creates test data.
        """
        self._mockgun = Mockgun(
            "https://test.shotgunstudio.com", login="user", password="1234"
        )
        self._user1 = self._mockgun.create("HumanUser", {"login": "user"})
        self._user2 = self._mockgun.create("HumanUser", {"login": None})

    def test_operator_is(self):
        """
        Ensure is operator work.
        """
        actual = self._mockgun.find("HumanUser", [["login", "is", "user"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_is_none(self):
        """
        Ensure is operator work when used with None.
        """
        actual = self._mockgun.find("HumanUser", [["login", "is", None]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_is_case_sensitivity(self):
        """
        Ensure is operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "is", "USER"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_is_not(self):
        """
        Ensure the is_not operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "is_not", "user"]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_is_not_none(self):
        """
        Ensure the is_not operator works when used with None.
        """
        actual = self._mockgun.find("HumanUser", [["login", "is_not", None]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_is_not_case_sensitivity(self):
        """
        Ensure the is_not operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "is_not", "USER"]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_in(self):
        """
        Ensure the in operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "in", ["user"]]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_in_none(self):
        """
        Ensure the in operator works with a list containing None.
        """
        actual = self._mockgun.find("HumanUser", [["login", "in", [None]]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_in_case_sensitivity(self):
        """
        Ensure the in operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "in", ["USER"]]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_not_in(self):
        """
        Ensure the not_in operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "not_in", ["foo"]]])
        expected = [
            {"type": "HumanUser", "id": self._user1["id"]},
            {"type": "HumanUser", "id": self._user2["id"]},
        ]
        self.assertEqual(expected, actual)

    def test_operator_not_in_none(self):
        """
        Ensure the not_not operator works with a list containing None.
        """
        actual = self._mockgun.find("HumanUser", [["login", "not_in", [None]]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_not_in_case_sensitivity(self):
        """
        Ensure the not_in operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "not_in", ["USER"]]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_contains(self):
        """
        Ensures the contains operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "contains", "se"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_contains_case_sensitivity(self):
        """
        Ensure the contains operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "contains", "SE"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_not_contains(self):
        """
        Ensure the not_contains operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "not_contains", "user"]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_not_contains_case_sensitivity(self):
        """
        Ensure the not_contains operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "not_contains", "USER"]])
        expected = [{"type": "HumanUser", "id": self._user2["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_starts_with(self):
        """
        Ensure the starts_with operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "starts_with", "us"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_starts_with_case_sensitivity(self):
        """
        Ensure the starts_with operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "starts_with", "US"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_ends_with(self):
        """
        Ensure the ends_with operator works.
        """
        actual = self._mockgun.find("HumanUser", [["login", "ends_with", "er"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)

    def test_operator_ends_with_case_sensitivity(self):
        """
        Ensure the starts_with operator is case insensitive.
        """
        actual = self._mockgun.find("HumanUser", [["login", "ends_with", "ER"]])
        expected = [{"type": "HumanUser", "id": self._user1["id"]}]
        self.assertEqual(expected, actual)


class TestMultiEntityFieldComparison(unittest.TestCase):
    """
    Ensures multi entity field comparison work.
    """

    def setUp(self):
        """
        Creates test data.
        """

        self._mockgun = Mockgun(
            "https://test.shotgunstudio.com", login="user", password="1234"
        )

        # Create two users to assign to the pipeline configurations.
        self._user1 = self._mockgun.create("HumanUser", {"login": "user1"})
        self._user2 = self._mockgun.create("HumanUser", {"login": "user2"})

        # Create pipeline configurations that are assigned none, one or two users.
        self._mockgun.create(
            "PipelineConfiguration", {"code": "with_user1", "users": [self._user1]}
        )

        self._mockgun.create(
            "PipelineConfiguration", {"code": "with_user2", "users": [self._user2]}
        )

        self._mockgun.create(
            "PipelineConfiguration",
            {"code": "with_both", "users": [self._user2, self._user1]},
        )

        self._mockgun.create(
            "PipelineConfiguration", {"code": "with_none", "users": []}
        )

    def test_find_by_sub_entity_field(self):
        """
        Ensures that queries on linked entity fields works.
        """
        items = self._mockgun.find(
            "PipelineConfiguration", [["users.HumanUser.login", "is", "user1"]]
        )
        self.assertEqual(len(items), 2)

        items = self._mockgun.find(
            "PipelineConfiguration", [["users.HumanUser.login", "is", "user2"]]
        )
        self.assertEqual(len(items), 2)

        items = self._mockgun.find(
            "PipelineConfiguration", [["users.HumanUser.login", "contains", "ser"]]
        )
        self.assertEqual(len(items), 3)

        # Lets get fancy a bit.
        items = self._mockgun.find(
            "PipelineConfiguration",
            [
                {
                    "filter_operator": "any",
                    "filters": [
                        ["users.HumanUser.login", "is", "user1"],
                        ["users.HumanUser.login", "is", "user2"],
                    ],
                }
            ],
        )
        self.assertEqual(len(items), 3)

        items = self._mockgun.find(
            "PipelineConfiguration",
            [
                {
                    "filter_operator": "all",
                    "filters": [
                        ["users.HumanUser.login", "is", "user1"],
                        ["users.HumanUser.login", "is", "user2"],
                    ],
                }
            ],
        )
        self.assertEqual(len(items), 1)

    def test_find_with_none(self):
        """
        Ensures comparison with multi-entity fields and None works.
        """
        items = self._mockgun.find(
            "PipelineConfiguration", [["users", "is", None]], ["users"]
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["users"], [])

        items = self._mockgun.find(
            "PipelineConfiguration", [["users", "is_not", None]], ["users"]
        )
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertTrue(len(item["users"]) > 0)


class TestMultiEntityFieldUpdate(unittest.TestCase):
    """
    Ensures multi entity field update modes work.
    """

    def setUp(self):
        """
        Creates test data.
        """

        self._mockgun = Mockgun(
            "https://test.shotgunstudio.com", login="user", password="1234"
        )

        # Create two versions to assign to the shot.
        self._version1 = self._mockgun.create("Version", {"code": "version1"})
        self._version2 = self._mockgun.create("Version", {"code": "version2"})
        self._version3 = self._mockgun.create("Version", {"code": "version3"})

        # remove 'code' field for later comparisons
        del self._version1["code"]
        del self._version2["code"]
        del self._version3["code"]

        # Create playlists
        self._add_playlist = self._mockgun.create(
            "Playlist",
            {"code": "playlist1", "versions": [self._version1, self._version2]},
        )
        self._remove_playlist = self._mockgun.create(
            "Playlist",
            {
                "code": "playlist1",
                "versions": [self._version1, self._version2, self._version3],
            },
        )
        self._set_playlist = self._mockgun.create(
            "Playlist",
            {"code": "playlist1", "versions": [self._version1, self._version2]},
        )

    def test_update_add(self):
        """
        Ensures that "add" multi_entity_update_mode works.
        """
        # Attempts to add _version2
        # It already exists on the playlist and should not be duplicated
        self._mockgun.update(
            "Playlist",
            self._add_playlist["id"],
            {"versions": [self._version2, self._version3]},
            multi_entity_update_modes={"versions": "add"},
        )

        playlist = self._mockgun.find_one(
            "Playlist", [["id", "is", self._add_playlist["id"]]], ["versions"]
        )
        self.assertEqual(
            playlist["versions"], [self._version1, self._version2, self._version3]
        )

    def test_update_remove(self):
        """
        Ensures that "remove" multi_entity_update_mode works.
        """
        self._mockgun.update(
            "Playlist",
            self._remove_playlist["id"],
            {"versions": [self._version2]},
            multi_entity_update_modes={"versions": "remove"},
        )

        playlist = self._mockgun.find_one(
            "Playlist", [["id", "is", self._remove_playlist["id"]]], ["versions"]
        )
        self.assertEqual(playlist["versions"], [self._version1, self._version3])

    def test_update_set(self):
        """
        Ensures that "set" multi_entity_update_mode works.
        """
        self._mockgun.update(
            "Playlist",
            self._set_playlist["id"],
            {"versions": [self._version2, self._version3]},
            multi_entity_update_modes={"versions": "set"},
        )

        playlist = self._mockgun.find_one(
            "Playlist", [["id", "is", self._set_playlist["id"]]], ["versions"]
        )
        self.assertEqual(playlist["versions"], [self._version2, self._version3])

    def test_batch_update(self):
        self._mockgun.batch(
            [
                {
                    "request_type": "update",
                    "entity_type": "Playlist",
                    "entity_id": self._set_playlist["id"],
                    "data": {"versions": [self._version1, self._version2]},
                    "multi_entity_update_modes": {"versions": "set"},
                }
            ]
        )
        playlist = self._mockgun.find_one(
            "Playlist", [["id", "is", self._set_playlist["id"]]], ["versions"]
        )
        self.assertEqual(playlist["versions"], [self._version1, self._version2])


class TestFilterOperator(unittest.TestCase):
    """
    Unit tests for the filter_operator filter syntax.
    """

    def setUp(self):
        """
        Creates tests data.
        """
        super(TestFilterOperator, self).setUp()

        self._mockgun = Mockgun(
            "https://test.shotgunstudio.com", login="user", password="1234"
        )

        self._prj1_link = self._mockgun.create("Project", {"name": "prj1"})

        self._prj2_link = self._mockgun.create("Project", {"name": "prj2"})

        self._shot1 = self._mockgun.create(
            "Shot",
            {
                "code": "shot1",
                "project": self._prj1_link,
                "description": "a",
                "sg_cut_order": 2,
            },
        )

        self._shot2 = self._mockgun.create(
            "Shot", {"code": "shot2", "project": self._prj1_link, "sg_cut_order": 1}
        )

        self._shot3 = self._mockgun.create(
            "Shot", {"code": "shot3", "project": self._prj2_link, "description": "b"}
        )

        self._user1 = self._mockgun.create(
            "HumanUser", {"login": "user1", "password_strength": 0.2}
        )

        self._user2 = self._mockgun.create(
            "HumanUser", {"login": "user2", "created_at": datetime.datetime(2025, 1, 1)}
        )

    def test_simple_filter_operators(self):
        """
        Tests a simple use of the filter_operator.
        """
        shots = self._mockgun.find(
            "Shot",
            [
                {
                    "filter_operator": "any",
                    "filters": [["code", "is", "shot1"], ["code", "is", "shot2"]],
                }
            ],
        )

        self.assertEqual(len(shots), 2)

        shots = self._mockgun.find(
            "Shot",
            [
                {
                    "filter_operator": "all",
                    "filters": [["code", "is", "shot1"], ["code", "is", "shot2"]],
                }
            ],
        )

        self.assertEqual(len(shots), 0)

    def test_ordered_filter_operator(self):
        """
        Test use of the order feature of filter_operator on supported data types.
        """
        find_args = ["Shot", [], ["code"]]

        # str field
        shots = self._mockgun.find(
            *find_args, order=[{"field_name": "description", "direction": "asc"}]
        )
        self.assertEqual([s["code"] for s in shots], ["shot2", "shot1", "shot3"])

        shots = self._mockgun.find(
            *find_args, order=[{"field_name": "description", "direction": "desc"}]
        )
        self.assertEqual([s["code"] for s in shots], ["shot3", "shot1", "shot2"])

        # int field
        shots = self._mockgun.find(
            *find_args, order=[{"field_name": "sg_cut_order", "direction": "asc"}]
        )
        self.assertEqual([s["code"] for s in shots], ["shot3", "shot2", "shot1"])

        # float field
        users = self._mockgun.find(
            "HumanUser",
            [],
            ["login"],
            order=[{"field_name": "password_strength", "direction": "asc"}],
        )
        self.assertEqual([u["login"] for u in users], ["user2", "user1"])

        # date_time field
        users = self._mockgun.find(
            "HumanUser",
            [],
            ["login"],
            order=[{"field_name": "created_at", "direction": "asc"}],
        )
        self.assertEqual([u["login"] for u in users], ["user1", "user2"])

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
                                ["project", "is", self._prj1_link],
                            ],
                        },
                        {
                            "filter_operator": "all",
                            "filters": [
                                ["code", "is", "shot3"],
                                ["project", "is", self._prj2_link],
                            ],
                        },
                    ],
                }
            ],
        )

        self.assertEqual(len(shots), 2)

    def test_invalid_operator(self):

        self.assertRaisesRegex(
            ShotgunError,
            "Unknown filter_operator type: bad",
            lambda: self._mockgun.find(
                "Shot", [{"filter_operator": "bad", "filters": []}]
            ),
        )

        self.assertRaisesRegex(
            ShotgunError,
            "Bad filter operator, requires keys 'filter_operator' and 'filters',",
            lambda: self._mockgun.find("Shot", [{}]),
        )


class TestConfig(unittest.TestCase):
    """
    Tests the shotgun._Config class
    """

    def test_set_server_params_with_regular_url(self):
        """
        Make sure it works with a normal URL.
        """
        mockgun = Mockgun("https://server.shotgunstudio.com/")
        self.assertEqual(mockgun.config.scheme, "https")
        self.assertEqual(mockgun.config.server, "server.shotgunstudio.com")
        self.assertEqual(mockgun.config.api_path, "/api3/json")

    def test_set_server_params_with_url_with_path(self):
        """
        Make sure it works with a URL with a path
        """
        mockgun = Mockgun("https://local/something/")
        self.assertEqual(mockgun.config.scheme, "https")
        self.assertEqual(mockgun.config.server, "local")
        self.assertEqual(mockgun.config.api_path, "/something/api3/json")


if __name__ == "__main__":
    unittest.main()
