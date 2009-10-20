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

#include <parsethread.h>
#include <pgsql.h>
#include <threadinfo.h>


/**
 * The core parse function.  Parses an XML file and stores it in the database according to
 * the xmlparser.xsl template.
 *
 * @param dbc         Database connection
 * @param xslt        Pointer to a parsed XSLT Stylesheet (xmlparser.xsl)
 * @param mtx_sysreg  Mutex locking to avoid simultaneous registration of systems, as they cannot
 *                    be in an SQL transaction (due to SHA1 sysid must be registered and visible ASAP)
 * @param submid      Submission ID, reference to the submissionqueue record
 * @param fname       Full path to the report XML file to be parsed
 *
 * @return Return values:
 *          STAT_SUCCESS : Successfully registered report
 *          STAT_XMLFAIL : Could not parse the XML report file
 *          STAT_SYSREG  : Failed to register the system into the systems or systems_hostname tables
 *          STAT_GENDB   : Failed to start an SQL transaction (BEGIN)
 *          STAT_RTEVRUNS: Failed to register the rteval run into rtevalruns or rtevalruns_details
 *          STAT_CYCLIC  : Failed to register the data into cyclic_statistics or cyclic_rawdata tables
 */
inline int parse_report(dbconn *dbc, xsltStylesheet *xslt, pthread_mutex_t *mtx_sysreg,
			unsigned int submid, const char *fname) {
	int syskey = -1, rterid = -1;
	int rc = -1;
	xmlDoc *repxml = NULL;

	repxml = xmlParseFile(fname);
	if( !repxml ) {
		fprintf(stderr, "** ERROR **  Could not parse XML file: %s\n", fname);
	        return STAT_XMLFAIL;
	}

	pthread_mutex_lock(mtx_sysreg);
	syskey = db_register_system(dbc, xslt, repxml);
	pthread_mutex_unlock(mtx_sysreg);
	if( syskey < 0 ) {
		fprintf(stderr, "** ERROR **  Failed to register system (XML file: %s)\n", fname);
		rc = STAT_SYSREG;
		goto exit;

	}

	if( db_begin(dbc) < 1 ) {
		rc = STAT_GENDB;
		goto exit;
	}

	rterid = db_register_rtevalrun(dbc, xslt, repxml, syskey, fname);
	if( rterid < 0 ) {
		fprintf(stderr, "** ERROR **  Failed to register rteval run (XML file: %s)\n",
			fname);
		db_rollback(dbc);
		rc = STAT_RTEVRUNS;
		goto exit;
	}

	if( db_register_cyclictest(dbc, xslt, repxml, rterid) != 1 ) {
		fprintf(stderr, "** ERROR **  Failed to register cyclictest data (XML file: %s)\n",
			fname);
		db_rollback(dbc);
		rc = STAT_CYCLIC;
		goto exit;
	}

	rc = STAT_SUCCESS;
	db_commit(dbc);

 exit:
	xmlFreeDoc(repxml);
	return rc;
}


/**
 * The parser thread.  This thread lives until a shutdown notification is received.  It pulls
 * messages on a POSIX MQ based message queue containing submission ID and full path to an XML
 * report to be parsed.
 *
 * @param thrargs Contains database connection, XSLT stylesheet, POSXI MQ descriptor, etc
 *
 * @return Returns 0 on successful operation, otherwise 1 on errors.
 */
void *parsethread(void *thrargs) {
	threadData_t *args = (threadData_t *) thrargs;
	parseJob_t jobinfo;

	while( !*(args->shutdown) ) {
		int len = 0;
		unsigned int prio = 0;

		// Retrieve a parse job from the message queue
		memset(&jobinfo, 0, sizeof(parseJob_t));
		errno = 0;
		len = mq_receive(args->msgq, (char *)&jobinfo, sizeof(parseJob_t), &prio);
		if( (len < 0) && errno != EAGAIN ) {
			fprintf(stderr, "** ERROR ** Could not receive the message from queue: %s\n",
				strerror(errno));
			pthread_exit((void *) 1);
		}

		// If we have a message, then process the parse job
		if( (errno != EAGAIN) && (len > 0) ) {
			int res = 0;

			// Mark the job as "in progress", if successful update, continue parsing it
			if( db_update_submissionqueue(args->dbc, jobinfo.submid, STAT_INPROG) ) {
				res = parse_report(args->dbc, args->xslt, args->mtx_sysreg,
						   jobinfo.submid, jobinfo.filename);
				// Set the status for the submission
				db_update_submissionqueue(args->dbc, jobinfo.submid, res);
			}
		} else {
			// If no message was retrieved, sleep for a little while
			sleep(5);
		}
	}
	pthread_exit((void *) 0);
}
