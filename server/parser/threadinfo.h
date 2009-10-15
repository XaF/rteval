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
 * @file   threadinfo.h
 * @author David Sommerseth <davids@redhat.com>
 * @date   Thu Oct 15 11:47:51 2009
 *
 * @brief  Shared info between the main() and parsethread() functions
 *
 */

#ifndef _THREADINFO_H
#define _THREADINFO_H

#include <pgsql.h>
#include <libxslt/transform.h>

/**
 *  States for the thread slots, also used to identify if the main program
 *  can assign a new job to a thread or not.
 *
 */
typedef enum { thrREADY,     /**< Set by main() - thread slot is ready for a job */
	       thrSTARTED,   /**< Set by main() - thread slot is assigned to a running thread*/
	       thrRUNNING,   /**< Set by parsethread() - thread started running */
	       thrCOMPLETE,  /**< Set by parsethread() on success - thread completed */
	       thrFAIL       /**< Set by parsethread() on failure - thread completed */
} threadState;


/**
 *  Thread slot information.  Each thread slot is assigned with one threadData_t element.
 *
 */
typedef struct {
	threadState status;           /**< State of the current thread */
	pthread_mutex_t *mtx_sysreg;  /**< Mutex locking, to avoid clashes with registering systems */
	unsigned int id;	      /**< Numeric ID for this thread */
	dbconn *dbc;                  /**< Database connection assigned to this thread */
	xsltStylesheet *xslt;         /**< XSLT stylesheet assigned to this thread */

	unsigned int submid;          /**< Work info: Numeric ID of the job being parsed */
	const char *filename;         /**< Work info: Full filename of the report to be parsed*/
} threadData_t;

#endif
