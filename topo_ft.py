#!/usr/bin/python

from mininet.topo import Topo
import re

# utility functions to assign/get DPIDs, ip addresses, mac addresses etc.

def location_to_dpid(core=None, pod=None, switch=None):
    if core is not None:
        return '0000000010%02x0000'%core
    else:
        return'000000002000%02x%02x'%(pod, switch)

def pod_name_to_location(name):
    match = re.match('p(\d+)_s(\d+)', name)
    pod, switch = match.group(1, 2)
    return int(pod), int(switch)

def is_core(dpid):
    return ((dpid & 0xFF000000) >> 24) == 0x10

def dpid_to_name(dpid):
    if is_core(dpid):
        core_num = (dpid & 0xFF0000) >> 16
        return 'c_s%d'%core_num
    else:
        pod = (dpid & 0xFF00) >> 8
        switch = (dpid & 0xFF)
        return 'p%d_s%d'%(pod, switch)

def host_to_ip(name):
    match = re.match('p(\d+)_s(\d+)_h(\d+)', name)
    pod, switch, host = match.group(1, 2, 3)
    return '10.%s.%s.%s'%(pod, switch, host)

def ip_to_mac(ip):
    match = re.match('10.(\d+).(\d+).(\d+)', ip)
    pod, switch, host = match.group(1, 2, 3)
    return location_to_mac(int(pod), int(switch), int(host))

def location_to_mac(pod, switch, host):
    return '00:00:00:%02x:%02x:%02x'%(pod, switch, host)

class FatTreeTopo(Topo):

    # build a fat tree topo of size k
    def __init__(self, k):
        super(FatTreeTopo, self).__init__()

        self.k = k

        pods = [self.make_pod(i) for i in range(k)]

        for core_num in range((k/2)**2):
            dpid = location_to_dpid(core=core_num)
            s = self.addSwitch('c_s%d'%core_num, dpid=dpid)

            stride_num = core_num // (k/2)
            for i in range(k):
                self.addLink(s, pods[i][stride_num])

    
    # makes a single pod with its k switches and (k/2)^2 hosts
    def make_pod(self, pod_num):
        lower_layer_switches = [
            self.addSwitch('p%d_s%d'%(pod_num, i), dpid=location_to_dpid(pod=pod_num, switch=i))
            for i in range(self.k / 2)
        ]

        for i, switch in enumerate(lower_layer_switches):
            for j in range(2, self.k / 2 + 2):
                h = self.addHost('p%d_s%d_h%d'%(pod_num, i, j),
                    ip='10.%d.%d.%d'%(pod_num, i, j),
                    mac=location_to_mac(pod_num, i, j))
                self.addLink(switch, h)
        
        upper_layer_switches = [
            self.addSwitch('p%d_s%d'%(pod_num, i), dpid=location_to_dpid(pod=pod_num, switch=i))
            for i in range(self.k / 2, self.k)
        ]

        for lower in lower_layer_switches:
            for upper in upper_layer_switches:
                self.addLink(lower, upper)

        return upper_layer_switches


topos = {
    'fattree': FatTreeTopo,
}
