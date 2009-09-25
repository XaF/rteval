#!/bin/sh

PYTHON_FILES="rteval_xmlrpc.py xmlrpc_API1.py xmlparser.py rtevaldb.py database.py"
XSLT_FILES="xmlparser.xsl"

XSLTDIR="/usr/share/rteval"

APACHECONF="apache-rteval.conf"
RTEVALCONF="rteval-xmlrpc.conf"

if [ $# != 1 ]; then
    echo "$0 </var/www/html/.... full path to the directory the XML-RPC server will reside>"
    exit
fi
INSTALLDIR="$1"

echo "Installing rteval XML-RPC server to: $1"
mkdir -p $1/
cp -v ${PYTHON_FILES} ${INSTALLDIR}/
echo

echo "Installing XSLT templates to ${XSLTDIR}"
cp -v ${XSLT_FILES} ${XSLTDIR}
echo

echo "Creating Apache config file: apache-rteval.conf"
escinstpath="$(echo ${INSTALLDIR} | sed -e 's/\//\\\\\//g')"
expr=$(echo "s/{_INSTALLDIR_}/${escinstpath}/")
eval "sed -e ${expr} ${APACHECONF}.tpl" > ${APACHECONF}
echo "Copy the apache apache-rteval.conf into your Apache configuration"
echo "directory and restart your web server"
echo

