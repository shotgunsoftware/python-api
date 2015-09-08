"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2015, Shotgun Software Inc

 Redistribution and use in source and binary forms, with or without
 modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this
    list of conditions and the following disclaimer.

  - Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.

  - Neither the name of the Shotgun Software Inc nor the names of its
    contributors may be used to endorse or promote products derived from this
    software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

-----------------------------------------------------------------------------



-----------------------------------------------------------------------------
M O C K G U N 
-----------------------------------------------------------------------------

Experimental software ahead!
----------------------------
Disclaimer! Mockgun is in its early stages of development. It is not fully 
compatible with the Shotgun API yet and we offer no guarantees at this point 
that future versions of Mockgun will be backwards compatible. Consider this 
alpha level software and use at your own risk. 


What is Mockgun?
----------------
Mockgun is a Shotgun API mocker. It's a class that has got *most* of the same
methods and parameters that the Shotgun API has got. Mockgun is essentially a 
Shotgun *emulator* that (for basic operations) looks and feels like Shotgun.

The primary purpose of Mockgun is to drive unit test rigs where it becomes
too slow, cumbersome or non-practical to connect to a real Shotgun. Using a 
Mockgun for unit tests means that a test can be rerun over and over again 
from exactly the same database state. This can be hard to do if you connect
to a live Shotgun instance.  


How do I use Mockgun?
---------------------
First of all, you need a Shotgun schema to run against. This will define
all the fields and entities that mockgun will use. Simply connect to 
your Shotgun site and use the generate_schema() method to download
the schema data:

    # connect to your site
    from shotgun_api3 import Shotgun
    sg = Shotgun("https://mysite.shotgunstudio.com", script_name="xyz", api_key="abc")
    
    # write out schema data to files
    from shotgun_api3.lib import mockgun
    mockgun.generate_schema(sg, "/tmp/schema", "/tmp/entity_schema")
    
Now that you have a schema, you can tell your mockgun instance about it.
We do this as a class-level operation, so that the consctructor can be 
exactly like the real Shotgun one:

    from shotgun_api3.lib import mockgun
    
    # tell mockgun about the schema
    mockgun.Shotgun.set_schema_paths("/tmp/schema", "/tmp/entity_schema")
    
    # we are ready to mock! 
    # this call will not connect to mysite, but instead create a 
    # mockgun instance which is connected to an *empty* shotgun site
    # which has got the same schema as mysite.
    sg = mockgun.Shotgun("https://mysite.shotgunstudio.com", script_name="xyz", api_key="abc")

    # now you can start putting stuff in
    print sg.create("HumanUser", {"firstname": "John", "login": "john"})
    # prints {'login': 'john', 'type': 'HumanUser', 'id': 1, 'firstname': 'John'}
 
    # and find what you have created
    print sg.find("HumanUser", [["login", "is", "john"]])
    prints [{'type': 'HumanUser', 'id': 1}]
    
That's it! Mockgun is used to run the Shotgun Pipeline Toolkit unit test rig.

Mockgun has a 'database' in the form of a dictionary stored in Mockgun._db
By editing this directly, you can modify the database without going through 
the API.


What are the limitations?
---------------------
There are many. Don't expect mockgun to be fully featured at this point.
Below is a non-exhaustive list of things that we still need to implement:

- Many find queries won't work
- Methods around session handling and authentication is not implemented
- Attachments and upload is rundimental at best
- Schema modification isn't most most likely will never be supported
- There is no validation or sanitation

"""

import os, datetime
import cPickle as pickle

from .. import sg_timezone, ShotgunError
from ..shotgun import _Config

# ----------------------------------------------------------------------------
# Version
__version__ = "0.0.1"

# ----------------------------------------------------------------------------
# Errors

class MockgunError(Exception):
    """
    Base for all Mockgun related API Errors.
    These are errors that relate to mockgun specifically, for example
    relating to mockups setup and initialization. For operational errors,
    mockgun raises ShotgunErrors just like the Shotgun API.
    """
    pass

# ----------------------------------------------------------------------------
# Utility methods

def generate_schema(shotgun, schema_file_path, schema_entity_file_path):
    """
    Helper method for mockgun.
    Generates the schema files needed by the mocker by connecting to a real shotgun
    and downloading the schema information for that site. Once the generated schema 
    files are being passed to mockgun, it will mimic the site's schema structure.
    
    :param sg_url: Shotgun site url
    :param sg_script: Script name to connect with
    :param sg_key: Script key to connect with
    :param schema_file_path: Path where to write the main schema file to
    :param schema_entity_file_path: Path where to write the entity schema file to
    """
    
    schema = shotgun.schema_read()
    fh = open(schema_file_path, "w")
    pickle.dump(schema, fh)
    fh.close()
        
    schema_entity = shotgun.schema_entity_read()
    fh = open(schema_entity_file_path, "w")
    pickle.dump(schema_entity, fh)
    fh.close()
    
# ----------------------------------------------------------------------------
# API

class Shotgun(object):
    """
    Mockgun is a mocked Shotgun API, designed for test purposes.
    It generates an object which looks and feels like a normal Shotgun API instance.
    Instead of connecting to a real server, it keeps all its data in memory in a way
    which makes it easy to introspect and test.
    
    The methods presented in this class reflect the Shotgun API and are therefore
    sparsely documented.
    
    Please note that this class is built for test purposes only and only creates an
    object which *roughly* resembles the Shotgun API - however, for most common 
    use cases, this is enough to be able to perform relevant and straight forward 
    testing of code.
    """

    __schema_path = None
    __schema_entity_path = None

    @classmethod
    def set_schema_paths(cls, schema_path, schema_entity_path):
        """
        Set the path where schema files can be found. This is done at the class
        level so all Shotgun instances will share the same schema.
        The responsability to generate and load these files is left to the user
        changing the default value.
        
        :param schema_path: Directory path where schema files are.
        """
        cls.__schema_path = schema_path
        cls.__schema_entity_path = schema_entity_path

    @classmethod
    def get_schema_paths(cls):
        """
        Returns a tuple with paths to the files which are part of the schema.
        These paths can then be used in generate_schema if needed.
        
        :returns: A tuple with schema_file_path and schema_entity_file_path
        """
        return (cls.__schema_path, cls.__schema_entity_path)

    def __init__(self,
                 base_url,
                 script_name=None,
                 api_key=None,
                 convert_datetimes_to_utc=True,
                 http_proxy=None,
                 ensure_ascii=True,
                 connect=True,
                 ca_certs=None,
                 login=None,
                 password=None,
                 sudo_as_login=None,
                 session_token=None,
                 auth_token=None):

        # emulate the config object in the Shotgun API.
        # these settings won't make sense for mockgun, but
        # having them present means code and get and set them
        # they way they would expect to in the real API.
        self.config = _Config()
        
        # load in the shotgun schema to associate with this Shotgun
        (schema_path, schema_entity_path) = self.get_schema_paths()

        if schema_path is None or schema_entity_path is None:
            raise MockgunError("Cannot create Mockgun instance because no schema files have been defined. "
                               "Before creating a Mockgun instance, please call Mockgun.set_schema_paths() "
                               "in order to specify which Shotgun schema Mockgun should operate against.")
        
        if not os.path.exists(schema_path):
            raise MockgunError("Cannot locate Mockgun schema file '%s'!" % schema_path)
             
        if not os.path.exists(schema_entity_path):
            raise MockgunError("Cannot locate Mockgun schema file '%s'!" % schema_entity_path)

        fh = open(schema_path, "r")
        try:
            self._schema = pickle.load(fh)
        finally:
            fh.close()
            
        fh = open(schema_entity_path, "r")
        try:
            self._schema_entity = pickle.load(fh)
        finally:
            fh.close() 

        # initialize the "database"
        self._db = dict((entity, {}) for entity in self._schema)

        # set some basic public members that exist in the Shotgun API
        self.base_url = base_url
        
        # bootstrap the event log
        # let's make sure there is at least one event log id in our mock db
        data = {}
        data["event_type"] = "Hello_Mockgun_World"
        data["description"] = "Mockgun was born. Yay."
        self.create("EventLogEntry", data)

        self.finds = 0

    ###################################################################################################
    # public API methods


    def schema_read(self):
        return self._schema

    def schema_field_create(self, entity_type, data_type, display_name, properties=None):
        raise NotImplementedError
    
    def schema_field_update(self, entity_type, field_name, properties):
        raise NotImplementedError

    def schema_field_delete(self, entity_type, field_name):
        raise NotImplementedError
    
    def schema_entity_read(self):
        return self._schema_entity

    def schema_field_read(self, entity_type, field_name=None):
        if field_name is None:
            return self._schema[entity_type]
        else:
            return dict((k, v) for k, v in self._schema[entity_type].items() if k == field_name)


    def find(self, entity_type, filters, fields=None, order=None, filter_operator=None, limit=0, retired_only=False, page=0):
        
        
        self.finds += 1
                
        self._validate_entity_type(entity_type)
        # do not validate custom fields - this makes it hard to mock up a field quickly
        #self._validate_entity_fields(entity_type, fields)
        
        if isinstance(filters, dict):
            # complex filter style!
            # {'conditions': [{'path': 'id', 'relation': 'is', 'values': [1]}], 'logical_operator': 'and'}
            
            resolved_filters = []
            for f in filters["conditions"]:
                
                if f["path"].startswith("$FROM$"):
                    # special $FROM$Task.step.entity syntax
                    # skip this for now
                    continue
                    
                if len(f["values"]) != 1:
                    # {'path': 'id', 'relation': 'in', 'values': [1,2,3]} --> ["id", "in", [1,2,3]]
                    resolved_filters.append([ f["path"], f["relation"], f["values"] ])
                else:
                    # {'path': 'id', 'relation': 'is', 'values': [3]} --> ["id", "is", 3]
                    resolved_filters.append([ f["path"], f["relation"], f["values"][0] ])
                
        else:
            # traditiona style sg filters
            resolved_filters = filters        
        
        # now translate ["field", "in", 2,3,4] --> ["field", "in", [2, 3, 4]]
        resolved_filters_2 = []
        for f in resolved_filters:
            
            if len(f) > 3:
                # ["field", "in", 2,3,4] --> ["field", "in", [2, 3, 4]]
                new_filter = [ f[0], f[1], f[2:] ]
            
            elif f[1] == "in" and not isinstance(f[2], list):
                # ["field", "in", 2] --> ["field", "in", [2]]
                new_filter = [ f[0], f[1], [ f[2] ] ]
            
            else:
                new_filter = f
                
            resolved_filters_2.append(new_filter)
            
        results = [row for row in self._db[entity_type].values() if self._row_matches_filters(entity_type, row, resolved_filters_2, filter_operator, retired_only)]
        
        if fields is None:
            fields = set(["type", "id"])
        else:
            fields = set(fields) | set(["type", "id"])
        
        val = [dict((field, self._get_field_from_row(entity_type, row, field)) for field in fields) for row in results]
    
        return val
    
    
    def find_one(self, entity_type, filters, fields=None, order=None, filter_operator=None, retired_only=False):
        results = self.find(entity_type, filters, fields=fields, order=order, filter_operator=filter_operator, retired_only=retired_only)
        return results[0] if results else None
    
    def batch(self, requests):
        results = []
        for request in requests:
            if request["request_type"] == "create":
                results.append(self.create(request["entity_type"], request["data"]))
            elif request["request_type"] == "update":
                # note: Shotgun.update returns a list of a single item
                results.append(self.update(request["entity_type"], request["entity_id"], request["data"])[0])
            elif request["request_type"] == "delete":
                results.append(self.delete(request["entity_type"], request["entity_id"]))
            else:
                raise ShotgunError("Invalid request type %s in request %s" % (request["request_type"], request))
        return results

    def create(self, entity_type, data, return_fields=None):
        
        # special handling of storage fields - if a field value
        # is a dict with a key local_path, then add fields 
        # local_path_linux, local_path_windows, local_path_mac 
        # as a reflection of this
        for d in data:
            if isinstance(data[d], dict) and "local_path" in data[d]:
                # partly imitate some of the business logic happening on the 
                # server side of shotgun when a file/link entity value is created
                if "local_storage" not in data[d]:
                    data[d]["local_storage"] = {"id": 0, "name": "auto_generated_by_mockgun", "type": "LocalStorage"}
                if "local_path_linux" not in data[d]:
                    data[d]["local_path_linux"] = data[d]["local_path"]
                if "local_path_windows" not in data[d]:
                    data[d]["local_path_windows"] = data[d]["local_path"]
                if "local_path_mac" not in data[d]:
                    data[d]["local_path_mac"] = data[d]["local_path"]
        
        self._validate_entity_type(entity_type)
        self._validate_entity_data(entity_type, data)
        self._validate_entity_fields(entity_type, return_fields)
        try:
            # get next id in this table
            next_id = max(self._db[entity_type]) + 1
        except ValueError:
            next_id = 1
        
        row = self._get_new_row(entity_type)
        
        self._update_row(entity_type, row, data)        
        row["id"] = next_id
        
        self._db[entity_type][next_id] = row
        
        if return_fields is None:
            result = dict((field, self._get_field_from_row(entity_type, row, field)) for field in data)
        else:
            result = dict((field, self._get_field_from_row(entity_type, row, field)) for field in return_fields)

        result["type"] = row["type"]
        result["id"] = row["id"]
        
        return result

    def update(self, entity_type, entity_id, data):
        self._validate_entity_type(entity_type)
        self._validate_entity_data(entity_type, data)
        self._validate_entity_exists(entity_type, entity_id)

        row = self._db[entity_type][entity_id]
        self._update_row(entity_type, row, data)

        return [dict((field, item) for field, item in row.items() if field in data or field in ("type", "id"))]

    def delete(self, entity_type, entity_id):
        self._validate_entity_type(entity_type)
        self._validate_entity_exists(entity_type, entity_id)
        
        row = self._db[entity_type][entity_id]
        if not row["__retired"]:
            row["__retired"] = True
            return True
        else:
            return False
    
    def revive(self, entity_type, entity_id):
        self._validate_entity_type(entity_type)
        self._validate_entity_exists(entity_type, entity_id)
        
        row = self._db[entity_type][entity_id]
        if row["__retired"]:
            row["__retired"] = False
            return True
        else:
            return False
    
    def upload(self, entity_type, entity_id, path, field_name=None, display_name=None, tag_list=None):
        raise NotImplementedError
    
    def upload_thumbnail(self, entity_type, entity_id, path, **kwargs):
        pass

    ###################################################################################################
    # internal methods and members

    def _validate_entity_type(self, entity_type):
        if entity_type not in self._schema:
            raise ShotgunError("%s is not a valid entity" % entity_type)
    
    def _validate_entity_data(self, entity_type, data):
        if "id" in data or "type" in data:
            raise ShotgunError("Can't set id or type on create or update")

        self._validate_entity_fields(entity_type, data.keys())

        for field, item in data.items():
            
            if item is None:
                # none is always ok
                continue
            
            field_info = self._schema[entity_type][field]

            if field_info["data_type"]["value"] == "multi_entity":
                if not isinstance(item, list):
                    raise ShotgunError("%s.%s is of type multi_entity, but data %s is not a list" % (entity_type, field, item))
                elif item and any(not isinstance(sub_item, dict) for sub_item in item):
                    raise ShotgunError("%s.%s is of type multi_entity, but data %s contains a non-dictionary" % (entity_type, field, item))
                elif item and any("id" not in sub_item or "type" not in sub_item for sub_item in item):
                    raise ShotgunError("%s.%s is of type multi-entity, but an item in data %s does not contain 'type' and 'id'" % (entity_type, field, item))
                elif item and any(sub_item["type"] not in field_info["properties"]["valid_types"]["value"] for sub_item in item):
                    raise ShotgunError("%s.%s is of multi-type entity, but an item in data %s has an invalid type (expected one of %s)" % (entity_type, field, item, field_info["properties"]["valid_types"]["value"]))
                
                
            elif field_info["data_type"]["value"] == "entity":
                if not isinstance(item, dict):
                    raise ShotgunError("%s.%s is of type entity, but data %s is not a dictionary" % (entity_type, field, item))
                elif "id" not in item or "type" not in item:
                    raise ShotgunError("%s.%s is of type entity, but data %s does not contain 'type' and 'id'" % (entity_type, field, item))
                #elif item["type"] not in field_info["properties"]["valid_types"]["value"]:
                #    raise ShotgunError("%s.%s is of type entity, but data %s has an invalid type (expected one of %s)" % (entity_type, field, item, field_info["properties"]["valid_types"]["value"]))

            else:
                try:
                    sg_type = field_info["data_type"]["value"]
                    python_type = {"number": int,
                                   "float": float,
                                   "checkbox": bool,
                                   "text": basestring,
                                   "serializable": dict,
                                   "date": datetime.date,
                                   "date_time": datetime.datetime,
                                   "url": dict}[sg_type]
                except KeyError:
                    raise ShotgunError("Field %s.%s: Handling for Shotgun type %s is not implemented" % (entity_type, field, sg_type)) 
                
                if not isinstance(item, python_type):
                    raise ShotgunError("%s.%s is of type %s, but data %s is not of type %s" % (entity_type, field, type(item), sg_type, python_type))

                # TODO: add check for correct timezone

    def _validate_entity_fields(self, entity_type, fields):
        self._validate_entity_type(entity_type)
        if fields is not None:
            valid_fields = set(self._schema[entity_type].keys())
            for field in fields:
                try:
                    field2, entity_type2, field3 = field.split(".", 2)
                    self._validate_entity_fields(entity_type2, [field3])
                except ValueError:
                    if field not in valid_fields and field not in ("type", "id"):
                        raise ShotgunError("%s is not a valid field for entity %s" % (field, entity_type))
            
    def _get_default_value(self, entity_type, field):
        field_info = self._schema[entity_type][field]
        if field_info["data_type"]["value"] == "multi_entity":
            default_value = []
        else:
            default_value = field_info["properties"]["default_value"]["value"]
        return default_value

    def _get_new_row(self, entity_type):
        row = {"type": entity_type, "__retired": False}
        for field in self._schema[entity_type]:
            field_info = self._schema[entity_type][field]
            if field_info["data_type"]["value"] == "multi_entity":
                default_value = []
            else:
                default_value = field_info["properties"]["default_value"]["value"]
            row[field] = default_value
        return row

    def _compare(self, field_type, lval, operator, rval):
        if field_type == "checkbox":
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
        elif field_type in ("float", "number", "date", "date_time"):
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            elif operator == "less_than":
                return lval < rval
            elif operator == "greater_than":
                return lval > rval
            elif operator == "between":
                return lval >= rval[0] and lval <= rval[1]
            elif operator == "not_between":
                return lval < rval[0] or lval > rval[1]
            elif operator == "in":
                return lval in rval
        elif field_type == "list":
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            elif operator == "in":
                return lval in rval
            elif operator == "not_in":
                return lval not in rval
        elif field_type == "entity_type":
            if operator == "is":
                return lval == rval
        elif field_type == "text":
            if operator == "is":
                return lval == rval
            elif operator == "is_not":
                return lval != rval
            elif operator == "in":
                return lval in rval            
            elif operator == "contains":
                return lval in rval
            elif operator == "not_contains":
                return lval not in rval
            elif operator == "starts_with":
                return lval.startswith(rval)
            elif operator == "ends_with":
                return lval.endswith(rval)
        elif field_type == "entity":
            if operator == "is":
                return lval["type"] == rval["type"] and lval["id"] == rval["id"]
            elif operator == "is_not":
                return lval["type"] != rval["type"] or lval["id"] != rval["id"]
            elif operator == "in":
                return all((lval["type"] == sub_rval["type"] and lval["id"] == sub_rval["id"]) for sub_rval in rval)
            elif operator == "type_is":
                return lval["type"] == rval
            elif operator == "type_is_not":
                return lval["type"] != rval
            elif operator == "name_contains":
                return rval in lval["name"]
            elif operator == "name_not_contains":
                return rval not in lval["name"]
            elif operator == "name_starts_with":
                return lval["name"].startswith(rval)
            elif operator == "name_ends_with":
                return lval["name"].endswith(rval)
        elif field_type == "multi_entity":
            if operator == "is":
                return rval["id"] in (sub_lval["id"] for sub_lval in lval)
            elif operator == "is_not":
                return rval["id"] not in (sub_lval["id"] for sub_lval in lval)

        raise ShotgunError("The %s operator is not supported on the %s type" % (operator, field_type))

    def _get_field_from_row(self, entity_type, row, field):
        # split dotted form fields        
        try:
            # is it something like sg_sequence.Sequence.code ?
            field2, entity_type2, field3 = field.split(".", 2)
            
            if field2 in row:
                
                field_value = row[field2]
                
                # all deep links need to be link fields
                if not isinstance(field_value, dict):                    
                    raise ShotgunError("Invalid deep query field %s.%s" % (entity_type, field))
                    
                # make sure that types in the query match type in the linked field
                if entity_type2 != field_value["type"]:
                    raise ShotgunError("Deep query field %s.%s does not match type "
                                       "with data %s" % (entity_type, field, field_value))
                     
                # ok so looks like the value is an entity link
                # e.g. db contains: {"sg_sequence": {"type":"Sequence", "id": 123 } }
                linked_row = self._db[ field_value["type"] ][ field_value["id"] ]
                if field3 in linked_row:
                    return linked_row[field3]
                else:
                    return None

            else:
                # sg returns none for unknown stuff
                return None
        
        except ValueError:
            # this is not a deep-linked field - just something like "code"
            if field in row:
                return row[field]
            else:
                # sg returns none for unknown stuff
                return None

    def _get_field_type(self, entity_type, field):
        # split dotted form fields
        try:
            field2, entity_type2, field3 = field.split(".", 2)
            return self._get_field_type(entity_type2, field3)
        except ValueError:
            return self._schema[entity_type][field]["data_type"]["value"]

    def _row_matches_filter(self, entity_type, row, filter):
        
        
        try:
            field, operator, rval = filter
        except ValueError:
            raise ShotgunError("Filters must be in the form [lval, operator, rval]")
        lval = self._get_field_from_row(entity_type, row, field)
        
        field_type = self._get_field_type(entity_type, field)
        
        # if we're operating on an entity, we'll need to grab the name from the lval's row
        if field_type == "entity":
            lval_row = self._db[lval["type"]][lval["id"]]
            if "name" in lval_row:
                lval["name"] = lval_row["name"]
            elif "code" in lval_row:
                lval["name"] = lval_row["code"]
        return self._compare(field_type, lval, operator, rval)

    def _row_matches_filters(self, entity_type, row, filters, filter_operator, retired_only):
                
        if retired_only and not row["__retired"] or not retired_only and row["__retired"]:
            # ignore retired rows unless the retired_only flag is set
            # ignore live rows if the retired_only flag is set
            return False
        elif filter_operator in ("all", None):
            return all(self._row_matches_filter(entity_type, row, filter) for filter in filters)
        elif filter_operator == "any":
            return any(self._row_matches_filter(entity_type, row, filter) for filter in filters)
        else:
            raise ShotgunError("%s is not a valid filter operator" % filter_operator)


    def _update_row(self, entity_type, row, data):
        for field in data:
            field_type = self._get_field_type(entity_type, field)
            if field_type == "entity" and data[field]:
                row[field] = {"type": data[field]["type"], "id": data[field]["id"]}
            elif field_type == "multi_entity":
                row[field] = [{"type": item["type"], "id": item["id"]} for item in data[field]]
            else:
                row[field] = data[field]
            

    def _validate_entity_exists(self, entity_type, entity_id):
        if entity_id not in self._db[entity_type]:
            raise ShotgunError("No entity of type %s exists with id %s" % (entity_type, entity_id))




