/*
 * Copyright (C) 2009 Red Hat Inc.
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

/**
 * @file   parsethread.c
 * @author David Sommerseth <davids@redhat.com>
 * @date   Thu Oct 15 11:52:10 2009
 *
 * @brief  Contains the "main" function which a parser threads runs
 *
 *
 */

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <assert.h>

#include <threadinfo.h>
#include <pgsql.h>


/**
 * The core parse function.  It is started via pthread_create() in the main() function.  The
 * input data contains information on the file to parse
 *
 * @param thrargs Pointer to a threadData_t struct which contains database connection, XSLT stylesheet
 *                parser and a full path filename to the report to parse
 *
 * @return Returns 0 on success, otherwise a positive integer defining which part it failed on.
 *         Exit codes:
 *              1: Could not parse the XML report file
 *              2: Failed to register the system into the systems or systems_hostname tables
 *              3: Failed to start an SQL transaction (BEGIN)
 *              4: Failed to register the rteval run into rtevalruns or rtevalruns_details tables
 *              5: Failed to register the cyclictest data into cyclic_statistics or cyclic_rawdata tables     
 */
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
		rc = 2;
		goto exit;

	}

	if( db_begin(thrdata->dbc) < 1 ) {
		thrdata->status = thrFAIL;
		rc = 3;
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
