# -*- coding: utf-8 -*-
#
#   Copyright 2012 - 2013   Raphaël Beamonte <raphael.beamonte@gmail.com>
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
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   For the avoidance of doubt the "preferred form" of this code is one which
#   is in an open unpatent encumbered format. Where cryptographic key signing
#   forms part of the process of creating an executable the information
#   including keys needed to generate an equivalently functional executable
#   are deemed to be part of the source code.
#

import os
import os.path

pathSave={}
def getcmdpath(which):
    """
    getcmdpath is a method which allows finding an executable in the PATH
    directories to call it from full path
    """
    if not pathSave.has_key(which):
        for path in os.environ['PATH'].split(':'):
            cmdfile = os.path.join(path, which)
            if os.path.isfile(cmdfile) and os.access(cmdfile, os.X_OK):
                pathSave[which] = cmdfile
                break
        if not pathSave[which]:
            raise RuntimeError, "Command '%s' is unknown on this system" % which
    return pathSave[which]

