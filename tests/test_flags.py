"""Test using the Shotgun API flags."""

import shotgun_api3
from shotgun_api3 import *
from shotgun_api3.lib.httplib2 import Http

import base

import logging

class TestFlags(base.LiveTestBase):

    def setUp(self):
        super(TestFlags, self).setUp()

        # We will need the created_at field for the shot
        fields = self.shot.keys()[:]
        fields.append('created_at')
        self.shot = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]], fields)


    def test_summary_include_archived_projects(self):
        """Test summary with 'include_archived_projects'"""

        if self.sg.server_caps.version > (5, 3, 13):
            # Ticket #25082 ability to hide archived projects in summary

            summaries = [{'field': 'id', 'type': 'count'}]
            grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
            filters = [['project', 'is', self.project]]

            # archive project
            self.sg.update('Project', self.project['id'], {'archived':True})

            # should get no result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_archived_projects=False)
            self.assertEquals(result['summaries']['id'], 0)

            # should get result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_archived_projects=True)
            self.assertEquals(result['summaries']['id'], 1)

            # setting defaults to True, should get result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping)
            self.assertEquals(result['summaries']['id'], 1)

            # reset project
            self.sg.update('Project', self.project['id'], {'archived':False})


    def test_summary_include_template_projects(self):
        """Test summary with 'include_template_projects'"""

        # Ticket #28441

        self.LOG.setLevel(logging.DEBUG)

        summaries = [{'field': 'id', 'type': 'count'}]
        grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
        filters = [['project', 'is', self.project]]

        # control
        result = self.sg.summarize('Shot',
                                   filters=filters,
                                   summary_fields=summaries,
                                   grouping=grouping)
        self.assertEquals(result['summaries']['id'], 1)

        # backwards-compatibility
        if self.sg.server_caps.version < (6, 0, 0):

            # flag should not be passed, should get result
            self.assertRaises(ShotgunError, self.sg.summarize, 'Shot',
                              filters=filters,
                              summary_fields=summaries,
                              grouping=grouping,
                              include_template_projects=True)

        # test new features
        if self.sg.server_caps.version >= (6, 0, 0):
            # set as template project
            self.sg.update('Project', self.project['id'], {'is_template':True})

            # should get result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_template_projects=True)
            self.assertEquals(result['summaries']['id'],  1)

            # should get no result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_template_projects=False)
            self.assertEquals(result['summaries']['id'], 0)

            # setting defaults to False, should get no result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping)
            self.assertEquals(result['summaries']['id'], 0)

            # reset project
            self.sg.update('Project', self.project['id'], {'is_template':False})

        self.LOG.setLevel(logging.WARN)


    def test_include_archived_projects(self):
        """Test find with 'include_archived_projects'"""

        # Ticket #25082

        filters = [['id', 'is', self.shot['id']]]

        if self.sg.server_caps.version > (5, 3, 13):

            # control
            result = self.sg.find_one('Shot',
                                      filters=filters)
            self.assertEquals(result['id'], self.shot['id'])

            # archive project 
            self.sg.update('Project', self.project['id'], {'archived':True})

            # should get no result
            result = self.sg.find_one('Shot',
                                      filters=filters,
                                      include_archived_projects=False)
            self.assertEquals(result, None)

            # should get result
            result = self.sg.find_one('Shot',
                                      filters=filters,
                                      include_archived_projects=True)
            self.assertEquals(result['id'], self.shot['id'])

            # setting defaults to True, should get result
            result = self.sg.find_one('Shot',
                                      filters=filters)
            self.assertEquals(result['id'], self.shot['id'])

            # reset project
            self.sg.update('Project', self.project['id'], {'archived':False})


    def test_include_template_projects(self):
        """Test find with 'include_template_projects'"""

        # Ticket #28441

        self.LOG.setLevel(logging.DEBUG)

        filters = [['id', 'is', self.shot['id']]]

        # control
        result = self.sg.find_one('Shot',
                          filters=filters)
        self.assertEquals(result['id'], self.shot['id'])

        # backwards-compatibility
        if self.sg.server_caps.version < (6, 0, 0):

            self.assertRaises(ShotgunError, self.sg.find_one, 'Shot',
                              filters=filters,
                              include_template_projects=True)

        # test new features
        if self.sg.server_caps.version >= (6, 0, 0):

            # set as template project 
            self.sg.update('Project', self.project['id'], {'is_template':True})

            # should get result
            result = self.sg.find_one('Shot',
                                      filters=filters,
                                      include_template_projects=True)
            self.assertEquals(result['id'], self.shot['id'])

            # should get no result
            result = self.sg.find_one('Shot',
                                      filters=filters,
                                      include_template_projects=False)
            self.assertEquals(result, None)

            # setting defaults to False, should get no result
            result = self.sg.find_one('Shot',
                                      filters=filters)
            self.assertEquals(result, None)

            # reset project
            self.sg.update('Project', self.project['id'], {'is_template':False})

        self.LOG.setLevel(logging.WARN)


    def test_find_template_project(self):
        """Test find the 'Template Project'"""

        # Ticket #28441

        if self.sg.server_caps.version >= (6, 0, 0):

            # find by name
            result = self.sg.find_one('Project', [['name', 'is', self.template_project['name']]])
            self.assertEquals(result['id'], self.template_project['id'])

            # find by ID
            result = self.sg.find_one('Project', [['id', 'is', self.template_project['id']]])
            self.assertEquals(result['id'], self.template_project['id'])

            # find attached entity
            result = self.sg.find_one(
                'Ticket',
                [
                    ['id', 'is', self.template_ticket['id']],
                    ['project.Project.name', 'is', 'Template Project'],
                    ['project.Project.layout_project', 'is', None]
                ]
            )
            self.assertEquals(result['id'], self.template_ticket['id'])
