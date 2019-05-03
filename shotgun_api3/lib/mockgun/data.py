"""
 -----------------------------------------------------------------------------
 Copyright (c) 2009-2017, Shotgun Software Inc

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
"""
# TODO: Python3 support
# TODO: Logging not printing
# TODO: Dump database ability
import cPickle as pickle
import os

from .errors import MockgunError
from .schema import SchemaFactory

# Highest protocol that Python 2.4 supports, which is the earliest version of Python we support.
# Actually, this is the same version that Python 2.7 supports at the moment!
_HIGHEST_24_PICKLE_PROTOCOL = 2


# Global private values to cache the schema in.
__schema, __schema_entity = None, None


def _get_schema(force=False):
    """
    _get_schema will get the schema from the SchemaFactory and cache it.

    :param bool force: If set, force will always query the latest schema from disk.
    :return: schema dictionary from disk
    """
    global __schema, __schema_entity
    from .mockgun import Shotgun
    if not __schema or force is True:
        schema_path, schema_entity_path = Shotgun.get_schema_paths()
        if not schema_path or not schema_entity_path:
            raise MockgunError("You must set the schema paths on the Mockgun instance first.")
        __schema, __schema_entity = SchemaFactory.get_schemas(schema_path, schema_entity_path)
    return __schema


def _get_schema_entity(force=False):
    """
    _get_schema_entity will get the schema_entity from the SchemaFactory and cache it.

    :param bool force: If set, force will always query the latest schema_entity from disk.
    :return: schema_entity dictionary from disk
    """
    global __schema, __schema_entity
    from .mockgun import Shotgun
    if not __schema_entity or force is True:
        schema_path, schema_entity_path = Shotgun.get_schema_paths()
        if not schema_path or not schema_entity_path:
            raise MockgunError("You must set the schema paths on the Mockgun instance first.")
        __schema, __schema_entity = SchemaFactory.get_schemas(schema_path, schema_entity_path)
    return __schema_entity


def _get_entity_fields(entity):
    """
    _get_entity_fields will return a list of the fields on an entity as strings
    :param str entity: Shotgun entity that we want the schema for
    :return: List of the field names for the provided entity
    :rtype: list[str]
    """
    schema = _get_schema()
    return schema[entity].keys()


def _read_data_(shotgun, entity):
    """
    _read_data_ will return all of the entries for the provided entity.
    It will get all fields for the entity from the Mockgun schema.

    :param shotgun: Shotgun instance used to query a live site
    :param str entity: Shotgun entity that we want the schema for
    :return: List of found entities
    :rtype: list[dict]
    """
    try:
        return shotgun.find(
            entity,
            filters=[],
            fields=_get_entity_fields(entity)
        )
    except Exception as err:
        print("    Exception: %s" % str(err))
        import traceback
        traceback.print_exc()
        return []


class DatabaseFactory(object):
    """
    Allows to instantiate a pickled database.
    """
    _database_cache = None
    _database_cache_path = None

    @classmethod
    def get_database(cls, database_path):
        """
        Retrieves the schemas from disk.

        :param str database_path: Path to the database.

        :returns: Dictionary holding the database.
        :rtype: dict
        """
        if not os.path.exists(database_path):
            raise MockgunError("Cannot locate Mockgun database file '%s'!" % database_path)

        # Poor man's attempt at a cache. All of our use cases deal with a single pair of files
        # for the duration of the unit tests, so keep a cache for both inputs. We don't want
        # to deal with ever growing caches anyway. Just having this simple cache has shown
        # speed increases of up to 500% for Toolkit unit tests alone.

        if database_path != cls._database_cache_path:
            cls._database_cache = cls._read_file(database_path)
            cls._database_cache_path = database_path

        return cls._database_cache

    @classmethod
    def _read_file(cls, path):
        fh = open(path, "rb")
        try:
            return pickle.load(fh)
        finally:
            fh.close()


# ----------------------------------------------------------------------------
# Utility methods
def generate_data(shotgun, data_file_path, entity_subset=None):
    """
    Helper method for mockgun.
    Generates the data files needed by the mocker by connecting to a real shotgun
    and downloading the information for that site. Once the generated data
    files are being passed to mockgun, it will mimic the site's database structure.

    :param shotgun: Shotgun instance
    :param data_file_path: Path where to write the main data file to
    :param entity_subset: Optional subset of entities to generate data for.
                          If not passed, it will default to all entities
    """

    if not entity_subset:
        entity_subset = _get_schema().keys()

    database = {}
    for entity in entity_subset:
        print("Requesting data for: %s" % entity)
        database[entity] = _read_data_(shotgun, entity)

    fh = open(data_file_path, "wb")
    try:
        pickle.dump(database, fh, protocol=_HIGHEST_24_PICKLE_PROTOCOL)
    finally:
        fh.close()

