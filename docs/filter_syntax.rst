.. _filter_syntax:

#############
Filter Syntax
#############

*************
Basic Filters
*************

Filters are represented as a list of conditions that will be combined using the supplied
filter_operator (``any`` or ``all``). Each condition follows the basic simple form::

    [<field>, <relation>, <value(s)>]

Example
=======
Using the default filter_operator ``"all"``, the following filters will return all Shots whose status
is "ip" AND is linked to Asset #9::

    filters = [
        ["sg_status_list", "is", "ip"],
        ["assets", "is", {"type": "Asset", "id": 9}]
    ]
    result = sg.find("Shot", filters)


***************
Complex Filters
***************

.. versionadded::3.0.11

Complex filters can be a dictionary that represents a complex sub-condition of the form::

    {"filter_operator": "any", "filters": [<list of conditions>]}

Example
=======
Using the default filter_operator ``"all"``, the following filters will return all Shots whose status
is "ip" AND is linked to either Asset #9 OR Asset #23::

    filters = [
        ["sg_status_list", "is", "ip"],
        {
            "filter_operator": "any",
            "filters": [
                ["assets", "is", {"type": "Asset", "id": 9}],
                ["assets", "is", {"type": "Asset", "id": 23}]
            ]
        }
    ]
    result = sg.find("Shot", filters)


***********************
Operators and Arguments
***********************

::

    Operator                    Arguments
    --------                    ---------
    'is'                        [field_value] | None
    'is_not'                    [field_value] | None
    'less_than'                 [field_value] | None
    'greater_than'              [field_value] | None
    'contains'                  [field_value] | None
    'not_contains'              [field_value] | None
    'starts_with'               [string]
    'ends_with'                 [string]
    'between'                   [[field_value] | None, [field_value] | None]
    'not_between'               [[field_value] | None, [field_value] | None]
    'in_last'                   [[int], 'HOUR' | 'DAY' | 'WEEK' | 'MONTH' | 'YEAR']
                                       # note that brackets are not literal (eg. ['start_date', 'in_last', 1, 'DAY'])
    'in_next'                   [[int], 'HOUR' | 'DAY' | 'WEEK' | 'MONTH' | 'YEAR']
                                       # note that brackets are not literal (eg. ['start_date', 'in_next', 1, 'DAY'])
    'in'                        [[field_value] | None, ...] # Array of field values
    'type_is'                   [string] | None             # Shotgun entity type
    'type_is_not'               [string] | None             # Shotgun entity type
    'in_calendar_day'           [int]                       # Offset (e.g. 0 = today, 1 = tomorrow,
                                                            # -1 = yesterday)
    'in_calendar_week'          [int]                       # Offset (e.g. 0 = this week, 1 = next week,
                                                            # -1 = last week)
    'in_calendar_month'         [int]                       # Offset (e.g. 0 = this month, 1 = next month,
                                                            # -1 = last month)
    'name_contains'             [string]
    'name_not_contains'         [string]
    'name_starts_with'          [string]
    'name_ends_with'            [string]


****************************
Valid Operators By Data Type
****************************

::

    addressing                  'is'
                                'is_not'
                                'contains'
                                'not_contains'
                                'in'
                                'type_is'
                                'type_is_not'
                                'name_contains'
                                'name_not_contains'
                                'name_starts_with'
                                'name_ends_with'

    checkbox                    'is'
                                'is_not'

    currency                    'is'
                                'is_not'
                                'less_than'
                                'greater_than'
                                'between'
                                'not_between'
                                'in'
                                'not_in'

    date                        'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'in_last'
                                'not_in_last'
                                'in_next'
                                'not_in_next'
                                'in_calendar_day'
                                'in_calendar_week'
                                'in_calendar_month'
                                'in_calendar_year'
                                'between'
                                'in'
                                'not_in'

    date_time                   'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'in_last'
                                'not_in_last'
                                'in_next'
                                'not_in_next'
                                'in_calendar_day'
                                'in_calendar_week'
                                'in_calendar_month'
                                'in_calendar_year'
                                'between'
                                'in'
                                'not_in'

    duration                    'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    entity                      'is'
                                'is_not'
                                'type_is'
                                'type_is_not'
                                'name_contains'
                                'name_not_contains'
                                'name_is'
                                'in'
                                'not_in'

    float                       'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    image                       'is' ** Note: For both 'is' and 'is_not', the only supported value is None,
                                'is_not' **  which supports detecting the presence or lack of a thumbnail.

    list                        'is'
                                'is_not'
                                'in'
                                'not_in'

    multi_entity                'is' ** Note:  when used on multi_entity, this functions as
                                                you would expect 'contains' to function
                                'is_not'
                                'type_is'
                                'type_is_not'
                                'name_contains'
                                'name_not_contains'
                                'in'
                                'not_in'

    number                      'is'
                                'is_not'
                                'less_than'
                                'greater_than'
                                'between'
                                'not_between'
                                'in'
                                'not_in'

    password                    ** Filtering by this data type field not supported

    percent                     'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    serializable                ** Filtering by this data type field not supported

    status_list                 'is'
                                'is_not'
                                'in'
                                'not_in'

    summary                     ** Filtering by this data type field not supported


    tag_list                    'is'  ** Note:  when used on tag_list, this functions as
                                                you would expect 'contains' to function
                                'is_not'
                                'name_contains'
                                'name_not_contains'
                                'name_id'

    text                        'is'
                                'is_not'
                                'contains'
                                'not_contains'
                                'starts_with'
                                'ends_with'
                                'in'
                                'not_in'


    timecode                    'is'
                                'is_not'
                                'greater_than'
                                'less_than'
                                'between'
                                'in'
                                'not_in'

    url                         ** Filtering by this data type field is not supported



*************************
Additional Filter Presets
*************************


As of Shotgun version 7.0 it is possible to also use filter presets. These presets provide a simple 
way to specify powerful query filters that would otherwise be costly and difficult to craft using 
traditional filters.

Multiple presets can be specified in cases where it makes sense.

Also, these presets can be used alongside normal filters. The result returned is an AND operation 
between the specified filters.

Example Uses
============

The following query will return the Version with the name 'ABC' that is linked to the latest entity 
created::

    additional_filter_presets = [
        {
            "preset_name": "LATEST",
            "latest_by":   "ENTITIES_CREATED_AT"
        }
    ]

    filters = [['code', 'is', 'ABC']]

    result = sg.find('Version', filters = filters, additional_filter_presets = additional_filter_presets)


The following query will find all CutItems associated to Cut #1 and return all Versions associated 
to the Shot linked to each of these CutItems::

    additional_filter_presets = [
        {
            "preset_name": "CUT_SHOT_VERSIONS",
            "cut_id":       1
        }
    ]

    result = sg.find('Version', additional_filter_presets = additional_filter_presets)

Available Filter Presets by Entity Type
=======================================

Allowed filter presets (and preset parameter values) depend on the entity type being searched.

The table bellow gives the details about which filter preset can be used on each entity type and 
with which parameters.

::

    Entity Type Preset Name       Preset Parameters   Allowed Preset Parameter Values
    ----------- -----------       -----------------   -------------------------------
    Cut         LATEST            [string] latest_by  'REVISION_NUMBER':
                                                        Returns the cuts that have the
                                                        highest revision number.
                                                        This is typically used with a query
                                                        filter that returns cuts with the
                                                        same value for a given field
                                                        (e.g. code field). This preset
                                                        therefore allows to get
                                                        the Cut of that set that has
                                                        the highest revision_number value.

    Version     CUT_SHOT_VERSIONS [int] cut_id        Valid Cut entity id.
                                                        Returns all Version entities
                                                        associated to the Shot entity
                                                        associated to the CutItems
                                                        of the given Cut.
                                                        This basically allows to find all
                                                        Versions associated to the given
                                                        Cut, via its CutItems.

                LATEST            [string] latest_by  'ENTITIES_CREATED_AT':
                                                        When dealing with multiple
                                                        Versions associated to a group
                                                        of entities, returns only the
                                                        last Version created for each
                                                        entity.
                                                        For example, when dealing with a
                                                        set of Shots, this preset allows
                                                        to find the latest Version created
                                                        for each of these Shots.

                                                      'BY_PIPELINE_STEP_NUMBER_AND_ENTITIES_CREATED_AT':
                                                        When dealing with multiple versions
                                                        associated to the same entity *and*
                                                        to Tasks, returns the Version
                                                        associated to the Task with highest
                                                        step.list_order.
                                                        If multiple Versions are found for
                                                        that step.list_order, only the
                                                        latest Version is returned.
                                                        This allows to isolate the Version
                                                        entity that is the farthest along
                                                        in the pipeline for a given entity.
                                                        For example, when dealing with a Shot
                                                        with multiple Versions, this preset
                                                        will return the Version associated
                                                        to the Task with the highest
                                                        step.list_order value.