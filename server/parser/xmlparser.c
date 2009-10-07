/*
 * Copyright (C) 2009 Red Hat Inc.
 *
 * David Sommerseth <davids@redhat.com>
 *
 * Parses summary.xml reports from rteval into a standardised XML format
 * which is useful when putting data into a database.
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <libxml/tree.h>
#include <libxslt/xsltInternals.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>

#include <xmlparser.h>

static char *encapsString(const char *str) {
        char *ret = NULL;

        if( str == NULL ) {
                return NULL;
        }

        ret = (char *) calloc(1, strlen(str)+4);
        assert( ret != NULL );

        snprintf(ret, strlen(str)+3, "'%s'", str);
        return ret;
}

static char *encapsInt(const unsigned int val) {
        char *buf = NULL;

        buf = (char *) calloc(1, 130);
        snprintf(buf, 128, "'%i'", val);
        return buf;
}


xmlDoc *parseToSQLdata(xsltStylesheet *xslt, xmlDoc *indata_d, parseParams *params) {
        xmlDoc *result_d = NULL;
        char *xsltparams[10];
        unsigned int idx = 0, idx_table = 0, idx_syskey = 0, idx_rterid = 0, idx_repfname = 0;

        if( params->table == NULL ) {
                fprintf(stderr, "Table is not defined\n");
                return NULL;
        }

        // Prepare XSLT parameters
        xsltparams[idx++] = "table\0";
        xsltparams[idx] = (char *) encapsString(params->table);
        idx_table = idx++;

        if( params->syskey > 0) {
                xsltparams[idx++] = "syskey\0";
                xsltparams[idx] = (char *) encapsInt(params->syskey);
                idx_syskey = idx++;
        }

        if( params->rterid > 0 ) {
                xsltparams[idx++] = "rterid";
                xsltparams[idx] = (char *) encapsInt(params->rterid);
                idx_rterid = idx++;
        }

        if( params->report_filename ) {
                xsltparams[idx++] = "report_filename";
                xsltparams[idx] = (char *) encapsString(params->report_filename);
                idx_repfname = idx++;
        }
        xsltparams[idx] = NULL;

        // Apply the XSLT template to the input XML data
        result_d = xsltApplyStylesheet(xslt, indata_d, (const char **)xsltparams);
        if( result_d == NULL ) {
                fprintf(stderr, "Failed applying XSLT template to input XML\n");
        }

        // Free memory we allocated via encapsString()/encapsInt()
        free(xsltparams[idx_table]);
        if( params->syskey ) {
                free(xsltparams[idx_syskey]);
        }
        if( params->rterid ) {
                free(xsltparams[idx_rterid]);
        }
        if( params->report_filename ) {
                free(xsltparams[idx_repfname]);
        }

        return result_d;
}
