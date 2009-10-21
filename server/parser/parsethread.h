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

#ifndef _PARSETHREAD_H
#define _PARSETHREAD_H

typedef enum { jbNONE, jbAVAIL } jobStatus;

/**
 * This struct is used for sending a parse job to a worker thread via POSIX MQ
 */
typedef struct {
        jobStatus status;                  /**< Info about if job information*/
        unsigned int submid;               /**< Work info: Numeric ID of the job being parsed */
        char clientid[256];                /**< Work info: Should contain senders hostname */
        char filename[4096];               /**< Work info: Full filename of the report to be parsed */
} parseJob_t;


void *parsethread(void *thrargs);

#endif
