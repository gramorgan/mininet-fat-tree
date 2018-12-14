# pox controller implementing dijkstra shortest-path routing
# morgan grant (mlgrant@ucsc.edu)

import topo_ft

import logging
import sys

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.openflow.nicira as nx
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr

log = core.getLogger()


# controller that installs two level routing table on each switch that connects
class install_2level(object):

    def __init__(self, topo):
        core.openflow.addListeners(self)
        self.topo = topo
        self.k = self.topo.k

    def _handle_ConnectionUp(self, event):
        name = topo_ft.dpid_to_name(event.dpid)
        dpid = event.dpid
        connection = event.connection
        if topo_ft.is_core(dpid):
            self.install_core(connection, dpid, name)
        else:
            self.install_pod(connection, dpid, name)

    # add a single route with the specified ip, mask and output port
    def add_route(self, connection, ip, mask, port, priority=100):
        msg = nx.nx_flow_mod()
        msg.priority = priority
        msg.match.append(nx.NXM_OF_ETH_TYPE(0x800))
        msg.match.append(nx.NXM_OF_IP_DST(ip, mask))
        msg.actions.append(of.ofp_action_output(port=port))
        connection.send(msg)
    
    # install routes onto a core switch
    def install_core(self, connection, dpid, name):
        for pod in range(self.k):
            self.add_route(connection, '10.%d.0.0'%pod, '255.255.0.0', pod+1)

    # install routes onto a pod switch
    def install_pod(self, connection, dpid, name):
        pod, switch = topo_ft.pod_name_to_location(name)
        # upper layer pod switch
        if switch >= self.k / 2:
            for subnet in range(self.k/2):
                self.add_route(connection, '10.%d.%d.0'%(pod, subnet), '255.255.255.0', subnet+1)
        # lower layer pod switch
        else:
            for host in range(2, self.k/2 + 2):
                self.add_route(connection, '10.%d.%d.%d'%(pod, switch, host), '255.255.255.255', host-1)
        for host in range(2, self.k/2 + 2):
            port =  (host - 2 + switch) % (self.k / 2) + (self.k / 2) + 1
            self.add_route(connection, '0.0.0.%d'%host, '0.0.0.255', port, 50)


def launch(topo=None, install=False):
    if not topo:
        log.error('need to specify a topo')       
        return
    topo_name, k = topo.split(',')
    topo = topo_ft.topos[topo_name](int(k))

    if install:
        core.registerNew(install_2level, topo)
    else:
        log.error('must install controller')
        return

    log.info('controller loaded')
