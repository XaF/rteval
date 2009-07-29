#
#   database.py
#   Library for processing results from XMLSQLparser and
#   query a PostgreSQL database based on the input data
#
#   Copyright 2009      David Sommerseth <davids@redhat.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import psycopg2
import types
from pprint import pprint
class Database(object):
    def __init__(self, host=None, port=None, user=None, password=None, database=None):
        dsnd = {}
        if host is not None:
            dsnd['host'] = host
            dsnd['sslmode'] = 'require'
        if port is not None:
            dsnd['port'] = str(port)
            dsnd['sslmode'] = 'require'
        if user is not None:
            dsnd['user'] = user
        if password is not None:
            dsnd['password'] = password
        if database is not None:
            dsnd['dbname'] = database

        dsn = " ".join(["%s='%s'" %(k,v) for (k,v) in dsnd.items()])
        self.conn = psycopg2.connect(dsn)


    def INSERT(self, sqlvars):
        #
        # Validate input data
        #
        if type(sqlvars) is not types.DictType:
            raise AttributeError,'Input parameter is not a Python dict'

        try:
            sqlvars['table']
            sqlvars['fields']
            sqlvars['records']
        except KeyError, err:
            raise KeyError, "Input dictionary do not contain a required element: %s", str(err)

        if type(sqlvars['fields']) is not types.ListType:
            raise AttributeError,"The 'fields' element is not a list of fields"

        if type(sqlvars['records']) is not types.ListType:
            raise AttributeError,"The 'records' element is not a list of fields"

        if len(sqlvars['records']) == 0:
            return True

        #
        # Build SQL template
        #
        sqlstub = "INSERT INTO %s (%s) VALUES (%s)" % (sqlvars['table'],
                                                       ",".join(sqlvars['fields']),
                                                       ",".join(["%%(%s)s" % f for f in sqlvars['fields']])
                                                       )

        # Get a database cursor
        curs = self.conn.cursor()

        #
        # Loop through all records and insert them into the database
        #
        results = []
        for rec in sqlvars['records']:
            if type(rec) is not types.ListType:
                raise AttributeError, "The field values inside the 'records' list must be in a list"

            # Create a dictionary, which will be used for the SQL operation
            values = {}
            for i in range(0, len(sqlvars['fields'])):
                values[sqlvars['fields'][i]] = rec[i]

            curs.execute(sqlstub, values)
            # FIXME: catch the result of all INSERTs, appending them to the results list

        # Commit the work
        self.conn.commit()
        return results
