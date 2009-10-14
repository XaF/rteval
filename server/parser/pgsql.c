/*
 * Copyright (C) 2009 Red Hat Inc.
 *
 * David Sommerseth <davids@redhat.com>
 *
 * Takes a standardised XML document (from parseToSQLdata()) and does
 * the database operations based on that input
 *
 * This application is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; version 2.
 *
 * This application is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <libpq-fe.h>

#include <libxml/parser.h>
#include <libxml/xmlsave.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>

#include <eurephia_nullsafe.h>
#include <eurephia_xml.h>
#include <eurephia_values.h>
#include <configparser.h>
#include <xmlparser.h>
#include <pgsql.h>

/**
 * Connect to a database, based on the given configuration
 *
 * @param cfg eurephiaVALUES containing the configuration
 *
 * @return Returns a database handler
 */
void *db_connect(eurephiaVALUES *cfg) {
	PGconn *dbc = NULL;

	dbc = PQsetdbLogin(eGet_value(cfg, "db_server"),
			   eGet_value(cfg, "db_port"),
			   NULL, /* pgopt */
			   NULL, /* pgtty */
			   eGet_value(cfg, "database"),
			   eGet_value(cfg, "db_username"),
			   eGet_value(cfg, "db_password"));

	if( !dbc ) {
		fprintf(stderr, "** ERROR ** Could not connect to the database (unknown reason)\n");
		exit(2);
	}

	if( PQstatus(dbc) != CONNECTION_OK ) {
		fprintf(stderr, "** ERROR ** Failed to connect to the database\n%s\n",
			PQerrorMessage(dbc));
		exit(2);
	}
	return dbc;
}


/**
 * Disconnect from the database
 *
 * @param dbc Pointer to the database handle to be disconnected.
 */
void db_disconnect(dbconn *dbc) {
	PQfinish((PGconn *) dbc);
}


/**
 * This function does INSERT SQL queries based on an XML document (sqldata) which contains
 * all information about table, fields and records to be inserted.  For security and performance,
 * this function uses prepared SQL statements.
 *
 * This function is PostgreSQL specific.
 *
 * @param dbc     Database handler to a PostgreSQL
 * @param sqldoc  sqldata XML document containing the data to be inserted.
 *
 * The sqldata XML document must be formated like this:
 * @code
 * <sqldata table="{table name}" [key="{field name}">
 *    <fields>
 *       <field fid="{integer}">{field name}</field>
 *       ...
 *       ...
 *       <field fid="{integer_n}">{field name 'n'}</field>
 *    </fields>
 *    <records>
 *       <record>
 *          <value fid="{integer} [type="{data type}"] [hash="{hash type}">{value for field 'fid'</value>
 *          ...
 *          ...
 *          <value fid="{integer_n}">{value for field 'fid_n'</value>
 *       </record>
 *       ...
 *       ...
 *       ...
 *    </records>
 * </sqldata>
 * @endcode
 * The 'sqldata' root tag must contain a 'table' attribute.  This must contain the a name of a table
 * in the database.  If the 'key' attribute is set, the function will return the that field value for
 * each INSERT query, using INSERT ... RETURNING {field name}.  The sqldata root tag must then have
 * two children, 'fields' and 'records'.
 *
 * The 'fields' tag need to contain 'field' children tags for each field to insert data for.  Each
 * field in the fields tag must be assigned a unique integer.
 *
 * The 'records' tag need to contain 'record' children tags for each record to be inserted.  Each
 * record tag needs to have 'value' tags for each field which is found in the 'fields' section.
 *
 * The 'value' tags must have a 'fid' attribute.  This is the link between the field name in the
 * 'fields' section and the value to be inserted.
 *
 * The 'type' attribute may be used as well, but the only supported data type supported to this
 * attribute is 'xmlblob'.  In this case, the contents of the 'value' tag must be more XML tags.
 * These tags will then be serialised to a string which is inserted into the database.
 *
 * The 'hash' attribute of the 'value' tag can be set to 'sha1'.  This will make do a SHA1 hash
 * calculation of the value and this hash value will be used for the insert.
 *
 * @return Returns an eurephiaVALUES list containing information about each record which was inserted.
 *         If the 'key' attribute is not set in the 'sqldata' tag, the OID value of each record will be
 *         saved.  If the table do not support OIDs, the value will be '0'.  Otherwise the contents of
 *         the defined field name will be returned.  If one of the INSERT queries fails, it will abort
 *         further processing and the function will return NULL.
 */
eurephiaVALUES *pgsql_INSERT(PGconn *dbc, xmlDoc *sqldoc) {
	xmlNode *root_n = NULL, *fields_n = NULL, *recs_n = NULL, *ptr_n = NULL, *val_n = NULL;
	char **field_ar = NULL, *fields = NULL, **value_ar = NULL, *values = NULL, *table = NULL, 
		tmp[20], *sql = NULL, *key = NULL;
	unsigned int fieldcnt = 0, *field_idx, i = 0;
	PGresult *dbres = NULL;
	eurephiaVALUES *res = NULL;

	assert( sqldoc != NULL );

	root_n = xmlDocGetRootElement(sqldoc);
	if( !root_n || (xmlStrcmp(root_n->name, (xmlChar *) "sqldata") != 0) ) {
		fprintf(stderr, "** ERROR ** Input XML document is not a valid sqldata document\n");
		return NULL;
	}

	table = xmlGetAttrValue(root_n->properties, "table");
	if( !table ) {
		fprintf(stderr, "** ERROR ** Input XML document is missing table reference\n");
		return NULL;
	}

	key = xmlGetAttrValue(root_n->properties, "key");

	fields_n = xmlFindNode(root_n, "fields");
	recs_n = xmlFindNode(root_n, "records");
	if( !fields_n || !recs_n ) {
		fprintf(stderr,
			"** ERROR ** Input XML document is missing either <fields/> or <records/>\n");
		return NULL;
	}

	// Count number of fields
	foreach_xmlnode(fields_n->children, ptr_n) {
		if( ptr_n->type == XML_ELEMENT_NODE ) {
			fieldcnt++;
		}
	}

	// Generate lists of all fields and a index mapping table
	field_idx = calloc(fieldcnt+1, sizeof(unsigned int));
	field_ar = calloc(fieldcnt+1, sizeof(char *));
	foreach_xmlnode(fields_n->children, ptr_n) {
		if( ptr_n->type != XML_ELEMENT_NODE ) {
			continue;
		}

		field_idx[i] = atoi_nullsafe(xmlGetAttrValue(ptr_n->properties, "fid"));
		field_ar[i] = xmlExtractContent(ptr_n);
		i++;
	}

	// Generate strings with field names and value place holders
	// for a prepared SQL statement
	fields = malloc_nullsafe(3);
	values = malloc_nullsafe(6*(fieldcnt+1));
	strcpy(fields, "(");
	strcpy(values, "(");
	int len = 3;
	for( i = 0; i < fieldcnt; i++ ) {
		// Prepare VALUES section
		snprintf(tmp, 6, "$%i", i+1);
		append_str(values, tmp, (6*fieldcnt));

		// Prepare fields section
		len += strlen_nullsafe(field_ar[i])+2;
		fields = realloc(fields, len);
		strcat(fields, field_ar[i]);

		if( i < (fieldcnt-1) ) {
			strcat(fields, ",");
			strcat(values, ",");
		}
	}
	strcat(fields, ")");
	strcat(values, ")");

	// Build up the SQL query
	sql = malloc_nullsafe( strlen_nullsafe(fields)
			       + strlen_nullsafe(values)
			       + strlen_nullsafe(table)
			       + strlen_nullsafe(key)
			       + 34 /* INSERT INTO  VALUES RETURNING*/
			       );
	sprintf(sql, "INSERT INTO %s %s VALUES %s", table, fields, values);
	if( key ) {
		strcat(sql, " RETURNING ");
		strcat(sql, key);
	}

	// Create a prepared SQL query
	dbres = PQprepare(dbc, "", sql, fieldcnt, NULL);
	if( PQresultStatus(dbres) != PGRES_COMMAND_OK ) {
		fprintf(stderr, "** ERROR **  Failed to prepare SQL query\n%s\n",
			PQresultErrorMessage(dbres));
		PQclear(dbres);
		goto exit;
	}
	PQclear(dbres);

	// Loop through all records and generate SQL statements
	res = eCreate_value_space(1);
	foreach_xmlnode(recs_n->children, ptr_n) {
		if( ptr_n->type != XML_ELEMENT_NODE ) {
			continue;
		}

		// Loop through all value nodes in each record node and get the values for each field
		value_ar = calloc(fieldcnt, sizeof(char *));
		i = 0;
		foreach_xmlnode(ptr_n->children, val_n) {
			char *fid_s = NULL;
			int fid = -1;

			if( i > fieldcnt ) {
				break;
			}

			if( val_n->type != XML_ELEMENT_NODE ) {
				continue;
			}

			fid_s = xmlGetAttrValue(val_n->properties, "fid");
			fid = atoi_nullsafe(fid_s);
			if( (fid_s == NULL) || (fid < 0) ) {
				continue;
			}
			value_ar[field_idx[i]] = sqldataExtractContent(val_n);
			i++;
		}

		// Insert the record into the database
		// fprintf(stderr, ".");
		dbres = PQexecPrepared(dbc, "", fieldcnt, (const char * const *)value_ar, NULL, NULL, 0);
		if( PQresultStatus(dbres) != (key ? PGRES_TUPLES_OK : PGRES_COMMAND_OK) ) {
			fprintf(stderr, "** ERROR **  Failed to do SQL INSERT query\n%s\n",
				PQresultErrorMessage(dbres));
			PQclear(dbres);
			eFree_values(res);
			res = NULL;

			// Free up the memory we've used for this record
			for( i = 0; i < fieldcnt; i++ ) {
				free_nullsafe(value_ar[i]);
			}
			free_nullsafe(value_ar);
			goto exit;
		}
		if( key ) {
			// If the /sqldata/@key attribute was set, fetch the returning ID
			eAdd_value(res, key, PQgetvalue(dbres, 0, 0));
		} else {
			static char oid[32];
			snprintf(oid, 30, "%ld%c", (unsigned long int) PQoidValue(dbres), 0);
			eAdd_value(res, "oid", oid);
		}
		PQclear(dbres);

		// Free up the memory we've used for this record
		for( i = 0; i < fieldcnt; i++ ) {
			free_nullsafe(value_ar[i]);
		}
		free_nullsafe(value_ar);
	}

 exit:
	free_nullsafe(sql);
	free_nullsafe(fields);
	free_nullsafe(values);
	free_nullsafe(field_ar);
	free_nullsafe(field_idx);
	return res;
}


/**
 * Start an SQL transaction (SQL BEGIN)
 *
 * @param dbc Database handler where to perform the SQL queries
 *
 * @return Returns 1 on success, otherwise -1 is returned
 */
int db_begin(dbconn *dbc) {
	PGresult *dbres = NULL;

	dbres = PQexec((PGconn *) dbc, "BEGIN");
	if( PQresultStatus(dbres) != PGRES_COMMAND_OK ) {
		fprintf(stderr, "** ERROR **  Failed to do prepare a transaction (BEGIN)\n%s\n",
			PQresultErrorMessage(dbres));
		PQclear(dbres);
		return -1;
	}
	PQclear(dbres);
	return 1;
}


/**
 * Commits an SQL transaction (SQL COMMIT)
 *
 * @param dbc Database handler where to perform the SQL queries
 *
 * @return Returns 1 on success, otherwise -1 is returned
 */
int db_commit(dbconn *dbc) {
	PGresult *dbres = NULL;

	dbres = PQexec((PGconn *) dbc, "COMMIT");
	if( PQresultStatus(dbres) != PGRES_COMMAND_OK ) {
		fprintf(stderr, "** ERROR **  Failed to do commit a database transaction (COMMIT)\n%s\n",
			PQresultErrorMessage(dbres));
		PQclear(dbres);
		return -1;
	}
	PQclear(dbres);
	return 1;
}


/**
 * Aborts an SQL transaction (SQL ROLLBACK/ABORT)
 *
 * @param dbc Database handler where to perform the SQL queries
 *
 * @return Returns 1 on success, otherwise -1 is returned
 */
int db_rollback(dbconn *dbc) {
	PGresult *dbres = NULL;

	dbres = PQexec((PGconn *) dbc, "ROLLBACK");
	if( PQresultStatus(dbres) != PGRES_COMMAND_OK ) {
		fprintf(stderr, "** ERROR **  Failed to do abort/rollback a transaction (ROLLBACK)\n%s\n",
			PQresultErrorMessage(dbres));
		PQclear(dbres);
		return -1;
	}
	PQclear(dbres);
	return 1;
}


/**
 * Registers information into the 'systems' and 'systems_hostname' tables, based on the
 * summary/report XML file from rteval.
 *
 * @param dbc        Database handler where to perform the SQL queries
 * @param xslt       A pointer to a parsed 'xmlparser.xsl' XSLT template
 * @param summaryxml The XML report from rteval
 *
 * @return Returns a value > 0 on success, which is a unique reference to the system of the report.
 *         If the function detects that this system is already registered, the 'syskey' reference will
 *         be reused.  On errors, -1 will be returned.
 */
int db_register_system(dbconn *dbc, xsltStylesheet *xslt, xmlDoc *summaryxml) {
	PGresult *dbres = NULL;
	eurephiaVALUES *dbdata = NULL;
	xmlDoc *sysinfo_d = NULL, *hostinfo_d = NULL;
	parseParams prms;
	char sqlq[4098];
	char *sysid = NULL;  // SHA1 value of the system id
	char *ipaddr = NULL, *hostname = NULL;
	int syskey = -1;

	memset(&prms, 0, sizeof(parseParams));
	prms.table = "systems";
	sysinfo_d = parseToSQLdata(xslt, summaryxml, &prms);
	if( !sysinfo_d ) {
		fprintf(stderr, "** ERROR **  Could not parse the input XML data\n");
		syskey= -1;
		goto exit;
	}
	sysid = sqldataGetValue(sysinfo_d, "sysid", 0);
	if( !sysid ) {
		fprintf(stderr, "** ERROR **  Could not retrieve the sysid field from the input XML\n");
		syskey= -1;
		goto exit;
	}

	memset(&sqlq, 0, 4098);
	snprintf(sqlq, 4096, "SELECT syskey FROM systems WHERE sysid = '%.256s'", sysid);
	free_nullsafe(sysid);
	dbres = PQexec((PGconn *) dbc, sqlq);
	if( PQresultStatus(dbres) != PGRES_TUPLES_OK ) {
		fprintf(stderr, "** ERROR **  SQL query failed: %s\n** ERROR **  %s\n",
			sqlq, PQresultErrorMessage(dbres));
		PQclear(dbres);
		syskey= -1;
		goto exit;
	}

	if( PQntuples(dbres) == 0 ) {  // No record found, need to register this system
		PQclear(dbres);

		dbdata = pgsql_INSERT((PGconn *) dbc, sysinfo_d);
		if( !dbdata ) {
			syskey= -1;
			goto exit;
		}
		if( (eCount(dbdata) != 1) || !dbdata->val ) { // Only one record should be registered
			fprintf(stderr, "** ERRORR **  Failed to register the system\n");
			eFree_values(dbdata);
			syskey= -1;
			goto exit;
		}
		syskey = atoi_nullsafe(dbdata->val);
		hostinfo_d = sqldataGetHostInfo(xslt, summaryxml, syskey, &hostname, &ipaddr);
		if( !hostinfo_d ) {
			syskey = -1;
			goto exit;
		}
		eFree_values(dbdata);

		dbdata = pgsql_INSERT((PGconn *) dbc, hostinfo_d);
		syskey = (dbdata ? syskey : -1);
		eFree_values(dbdata);

	} else if( PQntuples(dbres) == 1 ) { // System found - check if the host IP is known or not
		syskey = atoi_nullsafe(PQgetvalue(dbres, 0, 0));
		hostinfo_d = sqldataGetHostInfo(xslt, summaryxml, syskey, &hostname, &ipaddr);
		if( !hostinfo_d ) {
			syskey = -1;
			goto exit;
		}
		PQclear(dbres);

		// Check if this hostname and IP address is registered
		snprintf(sqlq, 4096,
			 "SELECT syskey FROM systems_hostname"
			 " WHERE hostname='%.256s' AND ipaddr='%.64s'",
			 hostname, ipaddr);

		dbres = PQexec((PGconn *) dbc, sqlq);
		if( PQresultStatus(dbres) != PGRES_TUPLES_OK ) {
			fprintf(stderr, "** ERROR **  SQL query failed: %s\n** ERROR **  %s\n",
				sqlq, PQresultErrorMessage(dbres));
			PQclear(dbres);
			syskey= -1;
			goto exit;
		}

		if( PQntuples(dbres) == 0 ) { // Not registered, then register it
			dbdata = pgsql_INSERT((PGconn *) dbc, hostinfo_d);
			syskey = (dbdata ? syskey : -1);
			eFree_values(dbdata);
		}
		PQclear(dbres);
	} else {
		// Critical -- system IDs should not be registered more than once
		fprintf(stderr, "** CRITICAL ERROR **  Multiple systems registered (%s)", sqlq);
		syskey= -1;
	}

 exit:
	free_nullsafe(hostname);
	free_nullsafe(ipaddr);
	if( sysinfo_d ) {
		xmlFreeDoc(sysinfo_d);
	}
	if( hostinfo_d ) {
		xmlFreeDoc(hostinfo_d);
	}
	return syskey;
}


/**
 * Registers information into the 'rtevalruns' and 'rtevalruns_details' tables
 *
 * @param dbc           Database handler where to perform the SQL queries
 * @param xslt          A pointer to a parsed 'xmlparser.xsl' XSLT template
 * @param summaryxml    The XML report from rteval
 * @param syskey        A positive integer containing the return value from db_register_system()
 * @param report_fname  A string containing the filename of the report.
 *
 * @return Returns a positive integer which references the 'rterid' value (RTEvalRunID) on success,
 *         otherwise -1 is returned.
 */
int db_register_rtevalrun(dbconn *dbc, xsltStylesheet *xslt, xmlDoc *summaryxml,
			  int syskey, const char *report_fname)
{
	int rterid = -1;
	xmlDoc *rtevalrun_d = NULL, *rtevalrundets_d = NULL;
	parseParams prms;
	eurephiaVALUES *dbdata = NULL;

	// Parse the rtevalruns information
	memset(&prms, 0, sizeof(parseParams));
	prms.table = "rtevalruns";
	prms.syskey = syskey;
	prms.report_filename = report_fname;
	rtevalrun_d = parseToSQLdata(xslt, summaryxml, &prms);
	if( !rtevalrun_d ) {
		fprintf(stderr, "** ERROR **  Could not parse the input XML data\n");
		rterid = -1;
		goto exit;
	}

	// Register the rteval run information
	dbdata = pgsql_INSERT((PGconn *) dbc, rtevalrun_d);
	if( !dbdata ) {
		rterid = -1;
		goto exit;
	}

	// Grab the rterid value from the database
	if( eCount(dbdata) != 1 ) {
		fprintf(stderr, "** ERROR ** Failed to register the rteval run\n");
		rterid = -1;
		eFree_values(dbdata);
		goto exit;
	}
	rterid = atoi_nullsafe(dbdata->val);
	if( rterid < 1 ) {
		fprintf(stderr, "** ERROR ** Failed to register the rteval run. Invalid rterid value.\n");
		rterid = -1;
		eFree_values(dbdata);
		goto exit;
	}
	eFree_values(dbdata);

	// Parse the rtevalruns_details information
	memset(&prms, 0, sizeof(parseParams));
	prms.table = "rtevalruns_details";
	prms.rterid = rterid;
	rtevalrundets_d = parseToSQLdata(xslt, summaryxml, &prms);
	if( !rtevalrundets_d ) {
		fprintf(stderr, "** ERROR **  Could not parse the input XML data (rtevalruns_details)\n");
		rterid = -1;
		goto exit;
	}

	// Register the rteval_details information
	dbdata = pgsql_INSERT((PGconn *) dbc, rtevalrundets_d);
	if( !dbdata ) {
		rterid = -1;
		goto exit;
	}

	// Check that only one record was inserted
	if( eCount(dbdata) != 1 ) {
		fprintf(stderr, "** ERROR ** Failed to register the rteval run\n");
		rterid = -1;
	}
	eFree_values(dbdata);

 exit:
	if( rtevalrun_d ) {
		xmlFreeDoc(rtevalrun_d);
	}
	if( rtevalrundets_d ) {
		xmlFreeDoc(rtevalrundets_d);
	}
	return rterid;
}


/**
 * Registers data returned from cyclictest into the database.
 *
 * @param dbc      Database handler where to perform the SQL queries
 * @param xslt       A pointer to a parsed 'xmlparser.xsl' XSLT template
 * @param summaryxml The XML report from rteval
 * @param rterid     A positive integer referencing the rteval run ID, returned from db_register_rtevalrun()
 *
 * @return Returns 1 on success, otherwise -1
 */
int db_register_cyclictest(dbconn *dbc, xsltStylesheet *xslt, xmlDoc *summaryxml, int rterid) {
	int result = -1;
	xmlDoc *cyclic_d = NULL;
	parseParams prms;
	eurephiaVALUES *dbdata = NULL;

	memset(&prms, 0, sizeof(parseParams));
	prms.table = "cyclic_statistics";
	prms.rterid = rterid;
	cyclic_d = parseToSQLdata(xslt, summaryxml, &prms);
	if( !cyclic_d ) {
		fprintf(stderr, "** ERROR **  Could not parse the input XML data\n");
		result = -1;
		goto exit;
	}

	// Register the cyclictest statistics information
	dbdata = pgsql_INSERT((PGconn *) dbc, cyclic_d);
	if( !dbdata ) {
		result = -1;
		goto exit;
	}
	if( eCount(dbdata) < 1 ) {
		fprintf(stderr, "** ERROR **  Failed to register cyclictest statistics\n");
		result = -1;
		eFree_values(dbdata);
		goto exit;
	}
	eFree_values(dbdata);
	xmlFreeDoc(cyclic_d);

	prms.table = "cyclic_rawdata";
	cyclic_d = parseToSQLdata(xslt, summaryxml, &prms);
	if( !cyclic_d ) {
		fprintf(stderr, "** ERROR **  Could not parse the input XML data\n");
		result = -1;
		goto exit;
	}

	// Register the cyclictest raw data
	dbdata = pgsql_INSERT((PGconn *) dbc, cyclic_d);
	if( !dbdata ) {
		result = -1;
		goto exit;
	}
	if( eCount(dbdata) < 1 ) {
		fprintf(stderr, "** ERROR **  Failed to register cyclictest raw data\n");
		result = -1;
		eFree_values(dbdata);
		goto exit;
	}
	eFree_values(dbdata);
	result = 1;
 exit:
	if( cyclic_d ) {
		xmlFreeDoc(cyclic_d);
	}

	return result;
}
