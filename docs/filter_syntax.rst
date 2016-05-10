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