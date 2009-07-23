#!/bin/sh

PYTHON_FILES="rteval_xmlrpc.py xmlrpc_API1.py"
HTACCESS="apache-htaccess"

if [ $# != 1 ]; then
    echo "$0 </var/www/html/.... path for the XML-RPC server to reside>"
    exit
fi
echo "Installing rteval XML-RPC server to: $1"

mkdir -p $1/
cp -v ${PYTHON_FILES} $1/
cp -v ${HTACCESS} $1/.htaccess
