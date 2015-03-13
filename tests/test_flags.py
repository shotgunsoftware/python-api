"""Test using the Shotgun API flags."""

import shotgun_api3
from shotgun_api3.lib.httplib2 import Http

import base

class TestFlags(base.LiveTestBase):
    def setUp(self):
        super(TestFlags, self).setUp()
        # We will need the created_at field for the shot
        fields = self.shot.keys()[:]
        fields.append('created_at')
        self.shot = self.sg.find_one('Shot', [['id', 'is', self.shot['id']]], fields)
        # We will need the uuid field for our LocalStorage
        fields = self.local_storage.keys()[:]
        fields.append('uuid')
        self.local_storage = self.sg.find_one('LocalStorage', [['id', 'is', self.local_storage['id']]], fields)

    def test_summary_include_archived_projects(self):
        """Test summary with 'include_archived_projects'"""

        if self.sg.server_caps.version > (5, 3, 13):
            # Ticket #25082 ability to hide archived projects in summary

            # archive project
            self.sg.update('Project', self.project['id'], {'archived':True})

            summaries = [{'field': 'id', 'type': 'count'}]
            grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
            filters = [['project', 'is', self.project]]

            # setting defaults to False, so we should get result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping)
            self.assertEqual(result['summaries']['id'],  1)

            # should get no result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_archived_projects=False)
            self.assertEqual(result['summaries']['id'],  0)

            # reset project
            self.sg.update('Project', self.project['id'], {'archived':False})

    def test_summary_include_template_projects(self):
        """Test summary with 'include_template_projects'"""

        if self.sg.server_caps.version > (6, 0, 0):
            # Ticket #28441

            # set as template project
            self.sg.update('Project', self.project['id'], {'template':True})

            summaries = [{'field': 'id', 'type': 'count'}]
            grouping = [{'direction': 'asc', 'field': 'id', 'type': 'exact'}]
            filters = [['project', 'is', self.project]]

            # setting defaults to False, so we should get no result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping)
            self.assertEqual(result['summaries']['id'],  0)

            # should get result
            result = self.sg.summarize('Shot',
                                       filters=filters,
                                       summary_fields=summaries,
                                       grouping=grouping,
                                       include_template_projects=False)
            self.assertEqual(result['summaries']['id'],  1)

            # reset project
            self.sg.update('Project', self.project['id'], {'template':False})

    def test_include_archived_projects(self):
        """Test find with 'include_archived_projects'"""

        if self.sg.server_caps.version > (5, 3, 13):
            # Ticket #25082

            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]])
            self.assertEquals(self.shot['id'], result['id'])

            # archive project 
            self.sg.update('Project', self.project['id'], {'archived':True})

            # setting defaults to True, so we should get result
            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]])
            self.assertEquals(self.shot['id'], result['id'])

            # should get no result
            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]], include_archived_projects=False)
            self.assertEquals(None, result)

            # reset project
            self.sg.update('Project', self.project['id'], {'archived':False})

    def test_include_template_projects(self):
        """Test find with 'include_template_projects'"""

        if self.sg.server_caps.version > (6, 0, 0):
            # Ticket #28441

            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]])
            self.assertEquals(self.shot['id'], result['id'])

            # set as template project 
            self.sg.update('Project', self.project['id'], {'is_template':True})

            # setting defaults to False, so we should not get result
            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]])
            self.assertEquals(None, result)

            # should get result
            result = self.sg.find_one('Shot', [['id','is',self.shot['id']]], include_template_projects=True)
            self.assertEquals(self.shot['id'], result['id'])

            # reset project
            self.sg.update('Project', self.project['id'], {'is_template':False})

