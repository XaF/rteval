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

#ifndef _XMLPARSER_H
#define _XMLPARSER_H

#define XSLTFILE "/usr/share/rteval/xmlparser.xsl"

typedef struct {
        char *table;
        unsigned int syskey;
        char *report_filename;
        unsigned int rterid;
} parseParams;

xmlDoc *parseToSQLdata(xsltStylesheet *xslt, xmlDoc *indata_d, parseParams *params);

#endif
