#!/bin/sh

PYTHON_FILES="rteval_xmlrpc.py xmlrpc_API1.py rtevaldb.py database.py"
XSLT_FILES="parser/xmlparser.xsl"

XSLTDIR="/usr/share/rteval"

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

./gen_config.sh ${INSTALLDIR}
