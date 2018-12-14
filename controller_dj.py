# pox controller implementing dijkstra shortest-path routing
# morgan grant (mlgrant@ucsc.edu)

import topo_ft

import logging
import sys

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr

log = core.getLogger()

# manages dijkstra routing for a single switch
class DijkstraSwitch(object):

    def __init__(self, connection, dpid, topo):
        connection.addListeners(self)
        self.connection = connection
        self.dpid = dpid
        self.topo = topo
        self.name = topo_ft.dpid_to_name(self.dpid)

        # dstip to output port mapping for this node
        self.table = {}

        _, prev = dijkstra(topo, self.name)

        for host in self.topo.hosts():
            u = host
            while prev[u] != self.name:
                u = prev[u]
            port, _ = self.topo.port(self.name, u)
            self.table[topo_ft.host_to_ip(host)] = port
        
    def _handle_PacketIn(self, event):
        ip = event.parsed.find('ipv4')
        if not ip:
            log.warning('got non-ip packet')
            return
        
        port = self.table[ip.dstip.toStr()]

        msg = of.ofp_packet_out()
        msg.data = event.ofp
        msg.actions.append(of.ofp_action_output(port=port))

        self.connection.send(msg)


# run dijkstra on a tolopogy with a given source node
def dijkstra(topo, source):
    nodes = topo.nodes()
    links = topo.links()

    dist = {}
    prev = {}
    Q = set()

    for node in nodes:
        dist[node] = float('inf')
        prev[node] = None
        Q.add(node)
    
    dist[source] = 0

    while len(Q) != 0:
        u = min({k:v for k, v in dist.items() if k in Q}, key=dist.get)
        Q.remove(u)

        neighbors = [n for n in nodes if (n, u) in links or (u, n) in links]
        for v in neighbors:
            if dist[u] + 1 < dist[v]:
                dist[v] = dist[u] + 1
                prev[v] = u
    
    return dist, prev


# register this controller to install dijkstra routing on each switch that connects
class install_dj(object):

    def __init__(self, topo):
        core.openflow.addListeners(self)
        self.topo = topo

    def _handle_ConnectionUp(self, event):
        connection = event.connection
        name = topo_ft.dpid_to_name(event.dpid)
        _, prev = dijkstra(self.topo, name)
        for host in self.topo.hosts():
            u = host
            while prev[u] != name:
                u = prev[u]
            port, _ = self.topo.port(name, u)

            msg = of.ofp_flow_mod()
            msg.match.dl_type = 0x800
            msg.match.nw_dst = IPAddr(topo_ft.host_to_ip(host))
            msg.actions.append(of.ofp_action_output(port=port))
            connection.send(msg)


# register this controller to run dijkstra routing from inside pox
class route_dj(object):

    def __init__(self, topo):
        core.openflow.addListeners(self)
        self.topo = topo
    
    def _handle_ConnectionUp(self, event):
        DijkstraSwitch(event.connection, event.dpid, self.topo)


def launch(topo=None, install=False):
    if not topo:
        log.error('need to specify a topo')       
        return
    topo_name, k = topo.split(',')
    topo = topo_ft.topos[topo_name](int(k))

    if install:
        core.registerNew(install_dj, topo)
    else:
        core.registerNew(route_dj, topo)

    log.info('controller loaded')
