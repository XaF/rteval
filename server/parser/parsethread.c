/*
 * Copyright (C) 2009 Red Hat Inc.
 *
 * David Sommerseth <davids@redhat.com>
 *
 * Contains the "main" functions a parser threads performs
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
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <assert.h>

#include <threadinfo.h>
#include <pgsql.h>



// For main program
#include <eurephia_nullsafe.h>
#include <eurephia_values.h>
#include <configparser.h>

#define XMLPARSER_XSL "xmlparser.xsl"


void *parsethread(void *thrargs) {
	threadData_t *thrdata = (threadData_t *) thrargs;
	int syskey = -1, rterid = -1;
	long rc = 9;
	xmlDoc *repxml = NULL;

	// fprintf(stderr, "--> Thread number: %i - Parsing: %s\n", thrdata->id, thrdata->filename);
	thrdata->status = thrRUNNING;

	repxml = xmlParseFile(thrdata->filename);
	if( !repxml ) {
		fprintf(stderr, "** ERROR **  Could not parse XML file: %s\n", thrdata->filename);
		thrdata->status = thrFAIL;
		pthread_exit((void *) 1);
	}

	pthread_mutex_lock(thrdata->mtx_sysreg);
	syskey = db_register_system(thrdata->dbc, thrdata->xslt, repxml);
	pthread_mutex_unlock(thrdata->mtx_sysreg);
	if( syskey < 0 ) {
		fprintf(stderr, "** ERROR **  Failed to register system (XML file; %s)\n",
			thrdata->filename);
		thrdata->status = thrFAIL;
		db_rollback(thrdata->dbc);
		rc = 3;
		goto exit;

	}

	if( db_begin(thrdata->dbc) < 1 ) {
		thrdata->status = thrFAIL;
		rc = 2;
		goto exit;
	}

	rterid = db_register_rtevalrun(thrdata->dbc, thrdata->xslt, repxml, syskey, thrdata->filename);
	if( rterid < 0 ) {
		fprintf(stderr, "** ERROR **  Failed to register rteval run (XML file; %s)\n",
			thrdata->filename);
		thrdata->status = thrFAIL;
		db_rollback(thrdata->dbc);
		rc = 4;
		goto exit;
	}

	if( db_register_cyclictest(thrdata->dbc, thrdata->xslt, repxml, rterid) != 1 ) {
		fprintf(stderr, "** ERROR **  Failed to register cyclictest data (XML file; %s)\n",
			thrdata->filename);
		thrdata->status = thrFAIL;
		db_rollback(thrdata->dbc);
		rc = 5;
		goto exit;
	}


	thrdata->status = thrCOMPLETE;
	rc = 0;
	db_commit(thrdata->dbc);

 exit:
	xmlFreeDoc(repxml);
	pthread_exit((void *) rc);
}
