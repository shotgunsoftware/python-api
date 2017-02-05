#! /opt/local/bin/python

#  -----------------------------------------------------------------------------
#  Copyright (c) 2009-2015, Shotgun Software Inc
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


def setUpModule():
    """
    Sets the Shotgun schema for this series of unit tests.
    """
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


class TestValidateFilterSyntax(TestBaseWithExceptionTests):
    """
    Tests filter syntax support.
    """

    def setUp(self):
        """
        Creates tests data.
        """
        super(TestValidateFilterSyntax, self).setUp()

        self._mockgun = Mockgun("https://test.shotgunstudio.com", login="user", password="1234")

        self._mockgun.create("Shot", {"code": "shot"})

    def test_filter_array_or_dict(self):
        # Should not throw, even though it is pretty much
        # empty.
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

        self.assertRaisesRegexp(
            ShotgunError,
            "Filters can only be lists or dictionaries, not int.",
            lambda: self._mockgun.find(
                "Shot",
                [1]
            )
        )


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
