/*
 * Copyright (C) 2009 Red Hat Inc.
 *
 * David Sommerseth <davids@redhat.com>
 *
 * Info used by the parsethread() function
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

#ifndef _THREADINFO_H
#define _THREADINFO_H

#include <pgsql.h>
#include <libxslt/transform.h>

typedef enum { thrINIT, thrSTARTED, thrRUNNING, thrCOMPLETE, thrFAIL } threadState;

typedef struct {
	threadState status;
	pthread_mutex_t *mtx_sysreg;
	unsigned int id;
	dbconn *dbc;
	xsltStylesheet *xslt;
	const char *filename;
} threadData_t;

#endif
