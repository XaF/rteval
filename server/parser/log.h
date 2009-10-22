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
 * @file   log.h
 * @author David Sommerseth <davids@redhat.com>
 * @date   Wed Oct 21 11:38:51 2009
 *
 * @brief  Generic log functions
 *
 */

#ifndef _RTEVAL_LOG_H
#define _RTEVAL_LOG_H

#include <pthread.h>
#include <syslog.h>

typedef enum { ltSYSLOG, ltFILE, ltCONSOLE } LogType;

typedef struct {
	LogType logtype;
	FILE *logfp;
	unsigned int verbosity;
	pthread_mutex_t *mtx_log;
} LogContext;


LogContext *init_log(const char *fname, const char *loglvl);
void close_log(LogContext *lctx);
void writelog(LogContext *lctx, unsigned int loglvl, const char *fmt, ... );

#endif
