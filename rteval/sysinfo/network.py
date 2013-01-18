# -*- coding: utf-8 -*-
#
#   Copyright 2009 - 2013   David Sommerseth <davids@redhat.com>
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

import ethtool, libxml2

class NetworkInfo(object):
    def __init__(self):
        pass

    def net_GetDefaultGW(self):
        # Get the interface name for the IPv4 default gw
        route = open('/proc/net/route')
        defgw4 = None
        if route:
            rl = route.readline()
            while rl != '' :
                rl = route.readline()
                splt = rl.split("\t")
                # Only catch default route
                if len(splt) > 2 and splt[2] != '00000000' and splt[1] == '00000000':
                    defgw4 = splt[0]
                    break
            route.close()
        return (defgw4, None) # IPv6 gw not yet implemented

    def MakeReport(self):
        ncfg_n = libxml2.newNode("NetworkConfig")
        (defgw4, defgw6) = self.net_GetDefaultGW()

        # Make an interface tag for each device found
        if hasattr(ethtool, 'get_interfaces_info'):
            # Using the newer python-ethtool API (version >= 0.4)
            for dev in ethtool.get_interfaces_info(ethtool.get_devices()):
                if cmp(dev.device,'lo') == 0:
                    continue

                intf_n = libxml2.newNode('interface')
                intf_n.newProp('device', dev.device)
                intf_n.newProp('hwaddr', dev.mac_address)
                ncfg_n.addChild(intf_n)

                # Protcol configurations
                if dev.ipv4_address:
                    ipv4_n = libxml2.newNode('IPv4')
                    ipv4_n.newProp('ipaddr', dev.ipv4_address)
                    ipv4_n.newProp('netmask', str(dev.ipv4_netmask))
                    ipv4_n.newProp('broadcast', dev.ipv4_broadcast)
                    ipv4_n.newProp('defaultgw', (defgw4 == dev.device) and '1' or '0')
                    intf_n.addChild(ipv4_n)

                for ip6 in dev.get_ipv6_addresses():
                    ipv6_n = libxml2.newNode('IPv6')
                    ipv6_n.newProp('ipaddr', ip6.address)
                    ipv6_n.newProp('netmask', str(ip6.netmask))
                    ipv6_n.newProp('scope', ip6.scope)
                    intf_n.addChild(ipv6_n)

        else: # Fall back to older python-ethtool API (version < 0.4)
            ifdevs = ethtool.get_active_devices()
            ifdevs.remove('lo')
            ifdevs.sort()

            for dev in ifdevs:
                intf_n = libxml2.newNode('interface')
                intf_n.newProp('device', dev.device)
                intf_n.newProp('hwaddr', dev.mac_address)
                ncfg_n.addChild(intf_n)

                ipv4_n = libxml2.newNode('IPv4')
                ipv4_n.newProp('ipaddr', ethtool.get_ipaddr(dev))
                ipv4_n.newProp('netmask', str(ethtool.get_netmask(dev)))
                ipv4_n.newProp('defaultgw', (defgw4 == dev) and '1' or '0')
                intf_n.addChild(ipv4_n)

        return ncfg_n


def unit_test(rootdir):
    import sys
    try:
        net = NetworkInfo()
        doc = libxml2.newDoc('1.0')
        cfg = net.MakeReport()
        doc.setRootElement(cfg)
        doc.saveFormatFileEnc('-', 'UTF-8', 1)

    except Exception, e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print "** EXCEPTION %s", str(e)
        return 1

if __name__ == '__main__':
    unit_test(None)

