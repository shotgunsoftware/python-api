.. _ami_handler:

###############################
Handling Action Menu Item Calls
###############################

This is an example ActionMenu Python class to handle the ``GET`` request sent from an
ActionMenuItem. It doesn't manage dispatching custom protocols but rather takes the arguments
from any ``GET`` data and parses them into the easily accessible and correctly typed instance
variables for your Python scripts.

Available as a Gist at https://gist.github.com/3253287

.. seealso::
    Our `support site has more information about Action Menu Items
    <https://developer.shotgridsoftware.com/python-api/cookbook/examples/ami_handler.html>`_.

************
GET vs. POST
************

Action Menu Items that open a url via `http` or `https` to another web server send their data
via ``POST``. If you're using a custom protocol the data is sent via ``GET``.

.. note::
    Browsers limit the length of a ``GET`` request. If you exceed this limit by attempting to
    select a lot of rows and launch your custom protocol, you may encounter
    "Failed to load resource" errors in your console.

.. seealso::
    This `Stack Overflow article "What is the maximum length of a URL in different browsers?"
    <http://stackoverflow.com/questions/417142/what-is-the-maximum-length-of-a-url-in-different-browsers>`_

::

    #!/usr/bin/env python
    # encoding: utf-8

    # ---------------------------------------------------------------------------------------------
    # Description
    # ---------------------------------------------------------------------------------------------
    """
    The values sent by the Action Menu Item are in the form of a GET request that is similar to the
    format: myCoolProtocol://doSomethingCool?user_id=24&user_login=shotgun&title=All%20Versions&...

    In a more human-readable state that would translate to something like this:
    {
        'project_name': 'Demo Project',
         'user_id': '24',
         'title': 'All Versions',
         'user_login': 'shotgun',
         'sort_column': 'created_at',
         'entity_type': 'Version',
         'cols': 'created_at',
         'ids': '5,2',
         'selected_ids': '2,5',
         'sort_direction': 'desc',
         'project_id': '4',
         'session_uuid': 'd8592bd6-fc41-11e1-b2c5-000c297a5f50',
         'column_display_names':
        [
            'Version Name',
             'Thumbnail',
             'Link',
             'Artist',
             'Description',
             'Status',
             'Path to frames',
             'QT',
             'Date Created'
        ]
    }

    This simple class parses the url into easy to access types variables from the parameters,
    action, and protocol sections of the url. This example url
    myCoolProtocol://doSomethingCool?user_id=123&user_login=miled&title=All%20Versions&...
    would be parsed like this:

        (string) protocol: myCoolProtocol
        (string) action: doSomethingCool
        (dict)   params: user_id=123&user_login=miled&title=All%20Versions&...

    The parameters variable will be returned as a dictionary of string key/value pairs. Here's
    how to instantiate:

      sa = ShotgunAction(sys.argv[1]) # sys.argv[1]

      sa.params['user_login'] # returns 'miled'
      sa.params['user_id'] # returns 123
      sa.protocol # returns 'myCoolProtocol'
    """


    # ---------------------------------------------------------------------------------------------
    # Imports
    # ---------------------------------------------------------------------------------------------
    import sys, os
    import six
    import logging as logger

    # ---------------------------------------------------------------------------------------------
    # Variables
    # ---------------------------------------------------------------------------------------------
    # location to write logfile for this script
    # logging is a bit of overkill for this class, but can still be useful.
    logfile = os.path.dirname(sys.argv[0]) + "/shotgun_action.log"


    # ----------------------------------------------
    # Generic ShotgunAction Exception Class
    # ----------------------------------------------
    class ShotgunActionException(Exception):
        pass


    # ----------------------------------------------
    # ShotgunAction Class to manage ActionMenuItem call
    # ----------------------------------------------
    class ShotgunAction:
        def __init__(self, url):
            self.logger = self._init_log(logfile)
            self.url = url
            self.protocol, self.action, self.params = self._parse_url()

            # entity type that the page was displaying
            self.entity_type = self.params["entity_type"]

            # Project info (if the ActionMenuItem was launched from a page not belonging
            # to a Project (Global Page, My Page, etc.), this will be blank
            if "project_id" in self.params:
                self.project = {
                    "id": int(self.params["project_id"]),
                    "name": self.params["project_name"],
                }
            else:
                self.project = None

            # Internal column names currently displayed on the page
            self.columns = self.params["cols"]

            # Human readable names of the columns currently displayed on the page
            self.column_display_names = self.params["column_display_names"]

            # All ids of the entities returned by the query (not just those visible on the page)
            self.ids = []
            if len(self.params["ids"]) > 0:
                ids = self.params["ids"].split(",")
                self.ids = [int(id) for id in ids]

            # All ids of the entities returned by the query in filter format ready
            # to use in a find() query
            self.ids_filter = self._convert_ids_to_filter(self.ids)

            # ids of entities that were currently selected
            self.selected_ids = []
            if len(self.params["selected_ids"]) > 0:
                sids = self.params["selected_ids"].split(",")
                self.selected_ids = [int(id) for id in sids]

            # All selected ids of the entities returned by the query in filter format ready
            # to use in a find() query
            self.selected_ids_filter = self._convert_ids_to_filter(self.selected_ids)

            # sort values for the page
            # (we don't allow no sort anymore, but not sure if there's legacy here)
            if "sort_column" in self.params:
                self.sort = {
                    "column": self.params["sort_column"],
                    "direction": self.params["sort_direction"],
                }
            else:
                self.sort = None

            # title of the page
            self.title = self.params["title"]

            # user info who launched the ActionMenuItem
            self.user = {"id": self.params["user_id"], "login": self.params["user_login"]}

            # session_uuid
            self.session_uuid = self.params["session_uuid"]

        # ----------------------------------------------
        # Set up logging
        # ----------------------------------------------
        def _init_log(self, filename="shotgun_action.log"):
            try:
                logger.basicConfig(
                    level=logger.DEBUG,
                    format="%(asctime)s %(levelname)-8s %(message)s",
                    datefmt="%Y-%b-%d %H:%M:%S",
                    filename=filename,
                    filemode="w+",
                )
            except IOError as e:
                raise ShotgunActionException("Unable to open logfile for writing: %s" % e)
            logger.info("ShotgunAction logging started.")
            return logger

            # ----------------------------------------------

        # Parse ActionMenuItem call into protocol, action and params
        # ----------------------------------------------
        def _parse_url(self):
            logger.info("Parsing full url received: %s" % self.url)

            # get the protocol used
            protocol, path = self.url.split(":", 1)
            logger.info("protocol: %s" % protocol)

            # extract the action
            action, params = path.split("?", 1)
            action = action.strip("/")
            logger.info("action: %s" % action)

            # extract the parameters
            # 'column_display_names' and 'cols' occurs once for each column displayed so we store it as a list
            params = params.split("&")
            p = {"column_display_names": [], "cols": []}
            for arg in params:
                key, value = map(six.moves.urllib.parse.unquote, arg.split("=", 1))
                if key == "column_display_names" or key == "cols":
                    p[key].append(value)
                else:
                    p[key] = value
            params = p
            logger.info("params: %s" % params)
            return (protocol, action, params)

        # ----------------------------------------------
        # Convert IDs to filter format to us in find() queries
        # ----------------------------------------------
        def _convert_ids_to_filter(self, ids):
            filter = []
            for id in ids:
                filter.append(["id", "is", id])
            logger.debug("parsed ids into: %s" % filter)
            return filter


    # ----------------------------------------------
    # Main Block
    # ----------------------------------------------
    if __name__ == "__main__":
        try:
            sa = ShotgunAction(sys.argv[1])
            logger.info("ShotgunAction: Firing... %s" % (sys.argv[1]))
        except IndexError as e:
            raise ShotgunActionException("Missing GET arguments")
        logger.info("ShotgunAction process finished.")
