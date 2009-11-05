#   configure.ac - autotools configuration file
#
#   Copyright 2009   David Sommerseth <davids@redhat.com>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#
#   To create the ./configure script you need to run 'autoreconf --install'
#

AC_INIT([rteval_parserd], [1.0], [davids@redhat.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign])
AC_PROG_CC

# Simple macro to abort on missing functions in libraries
AC_DEFUN([AX_msgMISSINGFUNC], AC_MSG_ERROR([Could not find function in library.  Aborting]))

# Check for libxml2
AC_CHECK_PROGS([XML2CFG], [xml2-config], [:])
if test "$XML2CFG" = :; then
   AC_MSG_ERROR([This package needs xml2-config from libxml2])
else
   AC_SUBST([LIBXSLT_INC], [$(xml2-config --cflags)])
fi
AC_CHECK_HEADERS([libxml/tree.h])
AC_CHECK_HEADERS([libxml/xmlsave.h])
AC_CHECK_HEADERS([libxml/xmlstring.h])
AC_CHECK_HEADERS([libxml/parser.h])
AC_CHECK_LIB([xml2],[xmlInitParser, xmlCleanupParser, xmlStrcmp, xmlFreeDoc, 
		     xmlSaveToBuffer, xmlSaveTree, xmlSaveClose, 
		     xmlBufferFree, xmlParseFile], 
		    [], AX_msgMISSINGFUNC)

# Check for libxslt
AC_CHECK_PROGS([XSLTCFG], [xslt-config], [:])
if test "$XSLTCFG" = :; then
   AC_MSG_ERROR([This package needs xslt-config from libxslt])
else
   AC_SUBST([LIBXSLT_INC], [$(xslt-config --cflags)])
fi
AC_CHECK_HEADERS([libxslt/xsltInternals.h])
AC_CHECK_HEADERS([libxslt/transform.h])
AC_CHECK_HEADERS([libxslt/xsltutils.h])
AC_CHECK_LIB([xslt], [xsltInit, xsltCleanupGlobals, xsltParseStylesheetFile,
		      xsltApplyStylesheet, xsltFreeStylesheet], 
		     [], AX_msgMISSINGFUNC())

# Check for libpq
AC_CHECK_PROGS([PGSQLCFG], [pg_config], [:])
if test "$PGSQLCFG" = :; then
   AC_MSG_ERROR([This package needs pg_config from PostgreSQL])
else
   AC_SUBST([LIBPQ_INC], [-I$(pg_config --includedir)])
fi
AC_CHECK_HEADERS([libpq-fe.h])
AC_CHECK_LIB([pq], [PQsetdbLogin, PQstatus, PQexec, PQreset, PQfinish,
		    PQprepare, PQexecPrepared, PQresultStatus, PQclear,
		    PQconsumeInput, PQnotifies, PQntuples],
		   [], AX_msgMISSINGFUNC())

# Check for POSIX features
AC_CHECK_HEADERS([mq.h])
AC_CHECK_LIB([rt], [mq_open, mq_close, mq_unlink, mq_send, mq_receive], [], AX_msgMISSINGFUNC())

AC_CHECK_HEADERS([pthread.h])
AC_CHECK_LIB([pthread], [pthread_attr_init, pthread_attr_setdetachstate, pthread_attr_destroy,
			 pthread_create, pthread_join,
			 pthread_mutex_lock, pthread_mutex_unlock],
			[], AX_msgMISSINGFUNC())

# Back to needed autotools stuff
AC_CONFIG_SRCDIR([rteval_parserd.c])
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_FILES([Makefile])

AC_OUTPUT
