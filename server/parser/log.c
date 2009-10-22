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

/**
 * Maps defined log level strings into syslog
 * compatible LOG_* integer values
 */
static struct {
	const char *priority_str;
	const int prio_level;
} syslog_prio_map[] = {
	{"emerg",     LOG_EMERG},
	{"emergency", LOG_EMERG},
	{"alert",     LOG_ALERT},
	{"crit",      LOG_CRIT},
	{"critical",  LOG_CRIT},
	{"err",       LOG_ERR},
	{"error",     LOG_ERR},
	{"warning",   LOG_WARNING},
	{"warn",      LOG_WARNING},
	{"notice",    LOG_NOTICE},
	{"info",      LOG_INFO},
	{"debug",     LOG_DEBUG},
	{NULL, 0}
};


LogContext *init_log(const char *fname, const char *loglvl) {
	LogContext *logctx = NULL;
	int i;

	logctx = (LogContext *) calloc(1, sizeof(LogContext)+2);
	assert( logctx != NULL);

	logctx->logfp = NULL;

	// Get the int value of the log level string
	logctx->verbosity = -1;
	if( loglvl ) {
		for( i = 0; syslog_prio_map[i].priority_str; i++ ) {
			if( strcasecmp(loglvl, syslog_prio_map[i].priority_str) == 0 ) {
				logctx->verbosity = syslog_prio_map[i].prio_level;
				break;
			}
		}
	}

	// If log level is not set, set LOG_INFo as default
	if( logctx->verbosity == -1 ) {
		logctx->verbosity = LOG_INFO;
	}

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
			switch( loglvl ) {
			case LOG_EMERG:
				fprintf(lctx->logfp, "**  EMERG  ERROR  ** ");
				break;
			case LOG_ALERT:
				fprintf(lctx->logfp, "**  ALERT  ERROR  ** ");
				break;
			case LOG_CRIT:
				fprintf(lctx->logfp, "** CRITICAL ERROR ** ");
				break;
			case LOG_ERR:
				fprintf(lctx->logfp, "** ERROR ** ");
				break;
			case LOG_WARNING:
				fprintf(lctx->logfp, "*WARNING* ");
				break;
			case LOG_NOTICE:
				fprintf(lctx->logfp, "[NOTICE] ");
				break;
			case LOG_INFO:
				fprintf(lctx->logfp, "[INFO]   ");
				break;
			case LOG_DEBUG:
				fprintf(lctx->logfp, "[DEBUG]  ");
				break;
			}
			vfprintf(lctx->logfp, fmt, ap);
			fprintf(lctx->logfp, "\n");
			pthread_mutex_unlock(lctx->mtx_log);

			if( lctx->logtype == ltFILE ) {
				fflush(lctx->logfp);
			}
			break;
		}
		va_end(ap);
	}
}
