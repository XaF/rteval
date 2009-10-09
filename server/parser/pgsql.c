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


PGconn *connectdb(eurephiaVALUES *cfg) {
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
	fprintf(stderr, "SQL: %s\n", sql);

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
	fprintf(stderr, "Doing inserts ");
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
	fprintf(stderr, " Done\n");

 exit:
	free_nullsafe(sql);
	free_nullsafe(fields);
	free_nullsafe(values);
	free_nullsafe(field_ar);
	free_nullsafe(field_idx);
	return res;
}
