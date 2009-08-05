#
#   rtevaldb.py
#   Function for registering a rteval summary.xml report into the database
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

from database import Database
from xmlparser import XMLSQLparser

def register_report(xslt, xmldata, filename, debug=False, noaction=False):
    dbc = Database(host="rtserver.farm.hsv.redhat.com", database="rteval",
                   user="xmlrpc", password="RTeval")
    dbc = Database(database="rteval", debug=debug, noaction=noaction)
    parser = XMLSQLparser(xslt, xmldata)

    systems = parser.GetSQLdata('systems')
    sysid = dbc.GetValue(systems, 0, 'sysid')

    # Check if system is already registered
    chk = dbc.SELECT('systems',['syskey'], where={'sysid': sysid})
    if dbc.NumTuples(chk) == 0:
        # This is a new system, register it
        res = dbc.INSERT(systems)
        if len(res) != 1:
            dbc.ROLLBACK()
            raise Exception, "** register_report():  Failed to register system [1]"

        syskey = res[0]
        systemhost = parser.GetSQLdata('systems_hostname', syskey=syskey)
        res = dbc.INSERT(systemhost)
        if len(res) != 1:
            dbc.ROLLBACK()
            raise Exception, "** register_report():  Failed to register system hostname/ipaddr [1]"

    else:
        # If this is a known system, check that hostname / IP address is the same
        syskey = dbc.GetValue(chk, 0, 0)
        systemhost = parser.GetSQLdata('systems_hostname', syskey=syskey)
        srch = {'hostname': dbc.GetValue(systemhost, 0, 'hostname'),
                'ipaddr': dbc.GetValue(systemhost, 0, 'ipaddr')}
        chk = dbc.SELECT('systems_hostname',['hostname','ipaddr'], where=srch)
        if dbc.NumTuples(chk) == 0:
            # This is an unknown hostname, register it
            dbc.INSERT(systemhost)

    # system is now registered, including hostname and IP address, and
    # we have a reference in the 'syskey' variable.

    # Register rteval run
    rterun = parser.GetSQLdata('rtevalruns', syskey=syskey, report_filename=filename)
    res = dbc.INSERT(rterun)
    if len(res) != 1:
        dbc.ROLLBACK()
        raise Exception, "** register_report(): Failed to register rteval run [1]"
    rterid = res[0]  # RTEval Run ID

    # Register some more details about the run
    rtedet = parser.GetSQLdata('rtevalruns_details', rterid=rterid)
    dbc.INSERT(rtedet)

    # Register cyclic statistics data
    cyclic = parser.GetSQLdata('cyclic_statistics', rterid=rterid)
    dbc.INSERT(cyclic)

    # Register cyclic raw data
    cycraw = parser.GetSQLdata('cyclic_rawdata', rterid=rterid)
    dbc.INSERT(cycraw)

    # Commit this work
    dbc.COMMIT()

    # We're done
    return (syskey, rterid)

