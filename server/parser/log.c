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
 * @file   log.c
 * @author David Sommerseth <davids@redhat.com>
 * @date   Wed Oct 21 11:38:51 2009
 *
 * @brief  Generic log functions
 *
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <assert.h>
#include <stdarg.h>
#include <pthread.h>
#include <syslog.h>

#include <eurephia_nullsafe.h>
#include <log.h>

LogContext *init_log(const char *fname, unsigned int verblvl) {
	LogContext *logctx = NULL;

	logctx = (LogContext *) calloc(1, sizeof(LogContext)+2);
	assert( logctx != NULL);

	logctx->logfp = NULL;
	logctx->verbosity = verblvl;

	if( fname == NULL ) {
		logctx->logtype = ltSYSLOG;
		openlog("rteval_parserd", LOG_PID, LOG_DAEMON);
	} else {
		if( strncmp(fname, "syslog:", 7) == 0 ) {
			const char *fac = fname+7;
			int facid = LOG_DAEMON;

			if( strcasecmp(fac, "local0") == 0 ) {
				facid = LOG_LOCAL0;
			} else if( strcasecmp(fac, "local1") == 0 ) {
				facid = LOG_LOCAL1;
			} else if( strcasecmp(fac, "local2") == 0 ) {
				facid = LOG_LOCAL2;
			} else if( strcasecmp(fac, "local3") == 0 ) {
				facid = LOG_LOCAL3;
			} else if( strcasecmp(fac, "local4") == 0 ) {
				facid = LOG_LOCAL4;
			} else if( strcasecmp(fac, "local5") == 0 ) {
				facid = LOG_LOCAL5;
			} else if( strcasecmp(fac, "local6") == 0 ) {
				facid = LOG_LOCAL6;
			} else if( strcasecmp(fac, "local7") == 0 ) {
				facid = LOG_LOCAL7;
			} else if( strcasecmp(fac, "user") == 0 ) {
				facid = LOG_USER;
			}
			logctx->logtype = ltSYSLOG;
			openlog("rteval_parserd", LOG_PID, facid);
		} else if( strcmp(fname, "stderr:") == 0 ) {
			logctx->logtype = ltCONSOLE;
			logctx->logfp = stderr;
		} else if( strcmp(fname, "stdout:") == 0 ) {
			logctx->logtype = ltCONSOLE;
			logctx->logfp = stdout;
		} else {
			logctx->logtype = ltFILE;
			logctx->logfp = fopen(fname, "a");
			if( logctx->logfp == NULL ) {
				fprintf(stderr, "** ERROR **  Failed to open log file %s: %s\n",
					fname, strerror(errno));
				free_nullsafe(logctx);
				return NULL;
			}
		}
	}

	if( logctx->logtype != ltSYSLOG ) {
		static pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;
		logctx->mtx_log = &mtx;
	}
	return logctx;
}


void close_log(LogContext *lctx) {
	if( !lctx ) {
		return;
	}

	switch( lctx->logtype ) {
	case ltFILE:
		fclose(lctx->logfp);
		break;

	case ltSYSLOG:
		closelog();
		break;

	case ltCONSOLE:
		break;
	}
	free_nullsafe(lctx);
}


void writelog(LogContext *lctx, unsigned int loglvl, const char *fmt, ... ) {
	if( !lctx || !fmt ) {
		return;
	}

	if( lctx->verbosity >= loglvl ) {
		va_list ap;

		va_start(ap, fmt);
		switch( lctx->logtype ) {
		case ltSYSLOG:
			vsyslog(loglvl, fmt, ap);
			break;

		case ltCONSOLE:
		case ltFILE:
			pthread_mutex_lock(lctx->mtx_log);
			vfprintf(lctx->logfp, fmt, ap);
			pthread_mutex_unlock(lctx->mtx_log);
			break;
		}
		va_end(ap);
	}
}
