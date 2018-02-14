#!/usr/bin/env python

"""
This script is a companion to the Shotgun Developer learning video titled,
"The Shotgun Python API, best practices" available here:

https://support.shotgunsoftware.com/hc/en-us/articles/115002525494-SG-Learning-Developer-Training

To learn more about this script, run `./best_practices.py -h` or
`./best_practices.py --help` for usage information.
"""

import os
import sys
import logging
import argparse
import shotgun_api3
from datetime import datetime

_DESCRIPTION = "This script runs various tests to demonstrate efficient use of \
the Shotgun Python API."


def _create_shots(sg, project):
    """
    Create 100 Shots in the specified Project.

    :param object sg: A Shotgun connection instance.
    :param dict project: A Shotgun Project.
    """

    batch_data = []

    for shot in range(1, 101):

        shot_name = "sh%s" % str(shot).zfill(3)

        batch_data.append({
            "request_type": "create",
            "entity_type": "Shot",
            "data": {
                "code": shot_name,
                "project": project,
            }
        })

    shots = sg.batch(batch_data)

    message = "Created Shots: %s." % [x["code"] for x in shots]

    logging.info(message)

    sg.create(
        "EventLogEntry",
        {
            "description": message,
            "project": project,
            "event_type": "API_Batch_Create",
            "meta": {
                "entity_types": ["Shot"],
                "shot_ids": [x["id"] for x in shots]
            }
        }
    )


def _find_shots(sg, project):
    """
    Find 100 Shots in the specified Project.

    :param object sg: A Shotgun connection instance.
    :param dict project: A Shotgun Project.
    """

    shots = sg.find(
        "Shot",
        [
            ["code", "in", ["sh%s" % str(x).zfill(3) for x in range(1, 100)]],
            ["project", "is", project],
        ],
        ["code"],
    )

    logging.info("Found Shots: %s." % [x["code"] for x in shots])


def _delete_shots(sg, project):
    """
    Deletes all Shots in a Project.

    :param object sg: A Shotgun connection instance.
    :param dict project: A Shotgun Project.
    """

    shots = sg.find("Shot", [["project", "is", project]], ["code"])

    batch_data = []

    for shot in shots:
        batch_data.append({
            "request_type": "delete",
            "entity_type": "Shot",
            "entity_id": shot["id"],
        })

    sg.batch(batch_data)

    message = "Deleted Shots: %s." % ["%s" % x["code"] for x in shots]

    logging.info(message)

    sg.create(
        "EventLogEntry",
        {
            "description": message,
            "project": project,
            "event_type": "API_Batch_Delete",
            "meta": {
                "entity_types": ["Shot"],
                "shot_ids": [x["id"] for x in shots]
            }
        }
    )


def _event_logs(sg, project):
    """
    Finds events.

    :param object sg: A Shotgun connection instance.
    :param dict project: A Shotgun Project.
    """

    events = sg.find(
        "EventLogEntry",
        [
            ["project", "is", project],
            ["event_type", "is", "Shotgun_Task_Change"],
            ["attribute_name", "is", "sg_status_list"],
            ["description", "contains", 'to "fin"'],
        ],
        [
            "id",
            "entity",
            "description",
            "created_at",
        ],
        order=[{"field_name": "created_at", "direction": "asc"}]
    )

    logging.info("Found event log entries: %s." % [x["id"] for x in events])


def _update_monkey_field(sg, project):
    """
    Update a monkey field.

    :param object sg: A Shotgun connection instance.
    :param dict project: A Shotgun Project.
    """

    message = "This is a monkey field update!"

    try:

        shot = sg.find_one(
            "Shot",
            [
                ["project", "is", project],
                ["sg_monkey", "is_not", message]
            ],
            ["code"],
        )

        if shot:
            sg.update(
                "Shot",
                shot["id"],
                {"sg_monkey": message},
            )
            logging.info("Updated the monkey field on %s." % shot["code"])
        else:
            logging.warning("Could not find Shot to update monkey field on.")

    except shotgun_api3.Fault, e:
        logging.error(
            "Could not update monkey field. Use the set_up_schema flag. Error: %s" % e
        )


def _set_up_schema(sg, project):

    try:
        sg.schema_field_read(
            "Shot",
            field_name="sg_monkey",
        )
        logging.info(
            "Shot entity type is already set up with the monkey field."
        )

    except shotgun_api3.Fault:
        sg.schema_field_create("Shot", "text", "monkey")
        logging.info("Added monkey field to Shot entity type.")


def _shortcuts(sg, project):
    """
    Demos some API shortcuts.
    """

    # Get the total number of Shots in our Project.
    num_shots = sg.summarize(
        "Shot",
        [["project", "is", project]],
        [{"field": "id", "type": "count"}],
    )
    logging.info("Found %s Shots.\n" % num_shots["summaries"]["id"])

    # Get all the replies on a Note.
    thread = sg.note_thread_read(6407)
    for note in thread:
        if note["type"] == "Reply":
            logging.info("  %s" % note["content"])
        else:
            logging.info("%s" % note["content"])

    # Share Shot sh001's thumbnail with the other Shots in our Project.
    source_shot = sg.find_one(
        "Shot",
        [
            ["code", "is", "sh001"],
            ["project", "is", project],
        ],
    )
    shots = sg.find(
        "Shot",
        [
            ["project", "is", project],
            ["id", "is_not", source_shot["id"]]
        ]
    )
    sg.share_thumbnail(shots, source_entity=source_shot)
    logging.info(
        "\nShared Shot with id %s's thumbnail with Shots with ids: %s." % (
            source_shot["id"],
            [x["id"] for x in shots],
        )
    )


def _set_up_logging():
    """
    Creates logs directory and sets up logging-related stuffs.
    """

    # Create a logs directory if it doesn't exist.
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create a datestamp var for stamping the logs.
    datestamp = datetime.now().strftime("%Y_%m_%d_%H-%M-%S")

    # Create a log file path.
    log = os.path.join("logs", "%s_%s.log" % (
        list(os.path.splitext(__file__))[0], datestamp)
    )

    # Set the logging level.
    logging_level = logging.DEBUG

    # Set up our logging.
    logging.basicConfig(
        filename=log,
        level=logging_level,
        format="%(levelname)s: %(asctime)s: %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())


def _set_up_parser():
    """
    :returns: dict of args.
    """

    # Initialize a command-line argument parser.
    parser = argparse.ArgumentParser(
        description=_DESCRIPTION
    )

    # Add create_shots argument to the parser.
    parser.add_argument(
        "-c",
        "--create_shots",
        help="Create 100 Shots in the specified Project.",
        action="store_true",
        required=False,
    )

    # Add find_shots argument to the parser.
    parser.add_argument(
        "-f",
        "--find_shots",
        help="Find 100 Shots in the specified Project.",
        action="store_true",
        required=False,
    )

    # Add project_id argument to the parser.
    parser.add_argument(
        "-p",
        "--project_id",
        help="The id of a Shotgun Project.",
        required=True,
    )

    # Add delete_shots argument to the parser.
    parser.add_argument(
        "-d",
        "--delete_shots",
        help="Delete all Shots in the specified Project.",
        action="store_true",
        required=False,
    )

    # Add event_logs argument to the parser.
    parser.add_argument(
        "-e",
        "--event_logs",
        help="Find event logs.",
        action="store_true",
        required=False,
    )

    # Add update_monkey_field argument to the parser.
    parser.add_argument(
        "-m",
        "--update_monkey_field",
        help="Update the monkey field on a Shot.",
        action="store_true",
        required=False,
    )

    # Add set_up_schema argument to the parser.
    parser.add_argument(
        "-su",
        "--set_up_schema",
        help="Create the monkey field on the Shot entity type.",
        action="store_true",
        required=False,
    )

    # Add quick argument to the parser.
    parser.add_argument(
        "-sc",
        "--shortcuts",
        help="Demo some useful API shortcuts.",
        action="store_true",
        required=False,
    )

    # Spit out script usage if no arguments are passed.
    if len(sys.argv) < 2:
        logging.info("Usage: %s --help" % __file__)
        sys.exit()

    # Resolve parser arguments.
    return vars(parser.parse_args())


def _get_sg_vars(args):
    """
    :returns: A shotgun connection object and Project dict, as a set.
    """

    # Grab a Shotgun connection.
    sg = shotgun_api3.Shotgun(
        os.environ["SG_SERVER"],
        script_name=os.environ["BEST_PRACTICES_NAME"],
        api_key=os.environ["BEST_PRACTICES_KEY"],
    )
    logging.debug("Created new Shotgun connection.")

    # Grab the specified Project dictionary and test our credentials.
    try:
        project = sg.find_one(
            "Project", [["id", "is", int(args["project_id"])]]
        )
        logging.debug(
            "Retrieved Project entity with id %s.\n" % args["project_id"]
        )
    except shotgun_api3.AuthenticationFault, e:
        print "Bad Shotgun credentials: %s" % e
        sys.exit()

    return sg, project


if __name__ == "__main__":

    # Initialize logging and create related folders/files.
    _set_up_logging()

    # Parse our user input and toss it in a dict.
    args = _set_up_parser()

    # Grab a Shotgun connection and vars to share.
    sg, project = _get_sg_vars(args)

    # Set up the schema for our monkey field.
    if args["set_up_schema"]:
        _set_up_schema(sg, project)

    # Run and time our _create_shots function, if requested.
    if args["create_shots"]:
        start = datetime.now()
        _create_shots(sg, project)
        logging.info(
            "_create_shots function took %s to complete." % str(datetime.now() - start)
        )

    # Run and time our _find_shots function, if requested.
    if args["find_shots"]:
        start = datetime.now()
        _find_shots(sg, project)
        logging.info(
            "_find_shots function took %s to complete." % str(datetime.now() - start)
        )

    # Run and time our _find_shots function, if requested.
    if args["delete_shots"]:
        start = datetime.now()
        _delete_shots(sg, project)
        logging.info(
            "_delete_shots function took %s to complete." % str(datetime.now() - start)
        )

    # Run and time our _event_logs function, if requested.
    if args["event_logs"]:
        start = datetime.now()
        _event_logs(sg, project)
        logging.info(
            "_delete_shots function took %s to complete." % str(datetime.now() - start)
        )

    # Run our _update_monkey_field function, if requested.
    if args["update_monkey_field"]:
        _update_monkey_field(sg, project)

    # Run our _quick function, if requested.
    if args["shortcuts"]:
        _shortcuts(sg, project)
