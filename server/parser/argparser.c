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
 * @file   argparser.c
 * @author David Sommerseth <davids@redhat.com>
 * @date   Thu Oct 22 13:58:46 2009
 *
 * @brief  Generic argument parser
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <eurephia_values.h>
#include <eurephia_nullsafe.h>

/**
 * Parses program arguments and puts the recognised arguments into an eurephiaVALUES struct.
 *
 * @param argc   argument counter
 * @param argv   argument string table
 *
 * @return Returns a pointer to an eurephiaVALUES struct.  On failure, the program halts.
 */
eurephiaVALUES *parse_arguments(int argc, char **argv) {
	eurephiaVALUES *args = NULL;
	int optidx, c, logset = 0;
	static struct option long_opts[] = {
		{"--log", 1, 0, 'l'},
		{"--log-level", 1, 0, 'L'},
		{"--config", 1, 0, 'f'},
		{"--daemon", 0, 0, 'd'},
		{0, 0, 0, 0}
	};

	args = eCreate_value_space(NULL, 21);
	eAdd_value(args, "daemon", "0");
	eAdd_value(args, "configfile", "/etc/rteval.conf");

	while( 1 ) {
		optidx = 0;
		c = getopt_long(argc, argv, "l:L:f:d", long_opts, &optidx);
		if( c == -1 ) {
			break;
		}

		switch( c ) {
		case 'l':
			eUpdate_value(args, "log", optarg, 1);
			logset = 1;
			break;
		case 'L':
			eUpdate_value(args, "loglevel", optarg, 1);
			break;
		case 'f':
			eUpdate_value(args, "configfile", optarg, 0);
			break;
		case 'd':
			eUpdate_value(args, "daemon", "1", 0);
			break;
		}
	}

	// If logging is not configured, and it is not run as a daemon
	// -> log to stderr:
	if( (eGet_value(args, "log") == NULL)
	    && (atoi_nullsafe(eGet_value(args, "daemon")) == 0) ) {
		eAdd_value(args, "log", "stderr:");
	}

	return args;
}
