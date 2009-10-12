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

#include <eurephia_nullsafe.h>
#include <eurephia_xml.h>
#include <xmlparser.h>
#include <sha1.h>


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


char *sqldataValueHash(xmlNode *sql_n) {
	const char *hash = NULL;
	SHA1Context shactx;
	uint8_t shahash[SHA1_HASH_SIZE];
	char *ret = NULL, *ptr = NULL;;
	int i;

	if( !sql_n || (xmlStrcmp(sql_n->name, (xmlChar *) "value") != 0)
	    || (xmlStrcmp(sql_n->parent->name, (xmlChar *) "record") != 0) ) {
		    return NULL;
	}

	hash = xmlGetAttrValue(sql_n->properties, "hash");
	if( !hash ) {
		// If no hash attribute is found, just use the raw data
		ret = strdup(xmlExtractContent(sql_n));
	} else if( strcasecmp(hash, "sha1") == 0 ) {
		const char *indata = xmlExtractContent(sql_n);
		// SHA1 hashing requested
		SHA1Init(&shactx);
		SHA1Update(&shactx, indata, strlen_nullsafe(indata));
		SHA1Final(&shactx, shahash);

		// "Convert" to a readable format
		ret = malloc_nullsafe((SHA1_HASH_SIZE * 2) + 3);
		ptr = ret;
		for( i = 0; i < SHA1_HASH_SIZE; i++ ) {
			sprintf(ptr, "%02x", shahash[i]);
			ptr += 2;
		}
	} else {
		ret = strdup("<Unsupported hashing algorithm>");
	}

	return ret;
}


char *sqldataExtractContent(xmlNode *sql_n) {
	const char *valtype = xmlGetAttrValue(sql_n->properties, "type");

	if( !sql_n || (xmlStrcmp(sql_n->name, (xmlChar *) "value") != 0)
	    || (xmlStrcmp(sql_n->parent->name, (xmlChar *) "record") != 0) ) {
		    return NULL;
	}

	if( valtype && (strcmp(valtype, "xmlblob") == 0) ) {
		xmlNode *chld_n = sql_n->children;

		// Go to next "real" tag, skipping non-element nodes
		while( chld_n && chld_n->type != XML_ELEMENT_NODE ){
			chld_n = chld_n->next;
		}
		return xmlNodeToString(chld_n);
	} else {
		return sqldataValueHash(sql_n);
	}
}


int sqldataGetFid(xmlNode *sql_n, const char *fname) {
	xmlNode *f_n = NULL;

	if( !sql_n || (xmlStrcmp(sql_n->name, (xmlChar *) "sqldata") != 0) ) {
		fprintf(stderr, "** ERROR ** Input XML document is not a valid sqldata document\n");
		return -2;
	}

	f_n = xmlFindNode(sql_n, "fields");
	if( !f_n || !f_n->children ) {
		fprintf(stderr, "** ERROR ** Input XML document does not contain a fields section\n");
		return -2;
	}

	foreach_xmlnode(f_n->children, f_n) {
		if( (f_n->type != XML_ELEMENT_NODE)
		    || xmlStrcmp(f_n->name, (xmlChar *) "field") != 0 ) {
			// Skip uninteresting nodes
			continue;
		}

		if( strcmp(xmlExtractContent(f_n), fname) == 0 ) {
			char *fid = xmlGetAttrValue(f_n->properties, "fid");
			if( !fid ) {
				fprintf(stderr, "** ERROR ** Field node is missing 'fid' attribute\n");
				return -2;
			}
			return atoi_nullsafe(fid);
		}
	}
	return -1;
}


char *sqldataGetValue(xmlDoc *sqld, const char *fname, int recid ) {
	xmlNode *r_n = NULL;
	int fid = -3, rc = 0;

	if( recid < 0 ) {
		fprintf(stderr, "** ERROR ** sqldataGetValue() :: Invalid recid\n");
		return NULL;
	}

	r_n = xmlDocGetRootElement(sqld);
	if( !r_n || (xmlStrcmp(r_n->name, (xmlChar *) "sqldata") != 0) ) {
		fprintf(stderr, "** ERROR ** Input XML document is not a valid sqldata document\n");
		return NULL;
	}

	fid = sqldataGetFid(r_n, fname);
	if( fid < 0 ) {
		return NULL;
	}

	r_n = xmlFindNode(r_n, "records");
	if( !r_n || !r_n->children ) {
		fprintf(stderr, "** ERROR ** Input XML document does not contain a records section\n");
		return NULL;
	}

	foreach_xmlnode(r_n->children, r_n) {
		if( (r_n->type != XML_ELEMENT_NODE)
		    || xmlStrcmp(r_n->name, (xmlChar *) "record") != 0 ) {
			// Skip uninteresting nodes
			continue;
		}
		if( rc == recid ) {
			xmlNode *v_n = NULL;
			// The rigth record is found, find the field we're looking for
			foreach_xmlnode(r_n->children, v_n) {
				char *fid_s = NULL;
				if( (v_n->type != XML_ELEMENT_NODE)
				    || (xmlStrcmp(v_n->name, (xmlChar *) "value") != 0) ) {
					// Skip uninteresting nodes
					continue;
				}
				fid_s = xmlGetAttrValue(v_n->properties, "fid");
				if( fid_s && (fid == atoi_nullsafe(fid_s)) ) {
					return sqldataExtractContent(v_n);
				}
			}
		}
		rc++;
	}
	return NULL;
}


xmlDoc *sqldataGetHostInfo(xsltStylesheet *xslt, xmlDoc *summaryxml,
			   int syskey, char **hostname, char **ipaddr)
{
	xmlDoc *hostinfo_d = NULL;
	parseParams prms;

	memset(&prms, 0, sizeof(parseParams));
	prms.table = "systems_hostname";
	prms.syskey = syskey;

	hostinfo_d = parseToSQLdata(xslt, summaryxml, &prms);
	if( !hostinfo_d ) {
		fprintf(stderr, "** ERROR **  Could not parse input XML data (hostinfo)\n");
		xmlFreeDoc(hostinfo_d);
		goto exit;
	}

	// Grab hostname from input XML
	*hostname = sqldataGetValue(hostinfo_d, "hostname", 0);
	if( !hostname ) {
		fprintf(stderr,
			"** ERROR **  Could not retrieve the hostname field from the input XML\n");
		xmlFreeDoc(hostinfo_d);
		goto exit;
	}

	// Grab ipaddr from input XML
	*ipaddr = sqldataGetValue(hostinfo_d, "ipaddr", 0);
	if( !ipaddr ) {
		fprintf(stderr,
			"** ERROR **  Could not retrieve the IP address field from the input XML\n");
		free_nullsafe(hostname);
		xmlFreeDoc(hostinfo_d);
		goto exit;
	}
 exit:
	return hostinfo_d;
}
