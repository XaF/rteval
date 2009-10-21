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

#ifndef _RTEVAL_PGSQL_H
#define _RTEVAL_PGSQL_H

#include <libpq-fe.h>
#include <libxml/parser.h>
#include <libxslt/transform.h>

#include <eurephia_values.h>
#include <parsethread.h>

#define STAT_NEW       0         /**< New, unparsed report in the submission queue */
#define STAT_ASSIGNED  1         /**< Submission is assigned to a parser */
#define STAT_INPROG    2         /**< Parsing has started */
#define STAT_SUCCESS   3         /**< Report parsed successfully */
#define STAT_UNKNFAIL  4         /**< Unkown failure */
#define STAT_XMLFAIL   5         /**< Failed to parse the report XML file */
#define STAT_SYSREG    6         /**< System registration failed */
#define STAT_RTERIDREG 7         /**< Failed to get a new rterid value for the rteval run */
#define STAT_GENDB     8         /**< General database error */
#define STAT_RTEVRUNS  9         /**< Registering rteval run information failed */
#define STAT_CYCLIC    10        /**< Registering cyclictest results failed */
#define STAT_REPMOVE   11        /**< Failed to move the report file */
typedef PGconn dbconn;           /**< Wrapper definition, for a more generic DB API */

/* Generic database function */
void *db_connect(eurephiaVALUES *cfg);
void db_disconnect(dbconn *dbc);
int db_begin(dbconn *dbc);
int db_commit(dbconn *dbc);
int db_rollback(dbconn *dbc);

/* rteval specific database functions */
parseJob_t *db_get_submissionqueue_job(dbconn *dbc, pthread_mutex_t *mtx);
int db_update_submissionqueue(dbconn *dbc, unsigned int submid, int status);
int db_register_system(dbconn *dbc, xsltStylesheet *xslt, xmlDoc *summaryxml);
int db_get_new_rterid(dbconn *dbc);
int db_register_rtevalrun(dbconn *dbc, xsltStylesheet *xslt, xmlDoc *summaryxml,
			  unsigned int submid, int syskey, int rterid, const char *report_fname);
int db_register_cyclictest(dbconn *dbc, xsltStylesheet *xslt, xmlDoc *summaryxml, int rterid);

#endif
