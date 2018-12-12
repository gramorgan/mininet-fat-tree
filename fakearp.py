# answers ARP requests with the mac address of each host as determined by fat tree topo
# hacked together from pieces of pox.proto.arp_responder

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.arp import arp
from pox.lib.addresses import EthAddr
from pox.lib.revent import EventHalt

from topo_ft import ip_to_mac

log = core.getLogger()

def _dpid_to_mac (dpid):
  return EthAddr("%012x" % (dpid & 0xffFFffFFffFF,))

class arp_responder(object):

	def __init__(self):
		core.openflow.addListeners(self)
	
	def _handle_ConnectionUp(self, event):
		fm = of.ofp_flow_mod()
		fm.priority = 0x7000 # Pretty high
		fm.match.dl_type = ethernet.ARP_TYPE
		fm.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
		event.connection.send(fm)

	def _handle_PacketIn(self, event):
		packet = event.parsed
		a = packet.find('arp')
		if not a: return

		r = arp()
		r.hwtype = a.hwtype
		r.prototype = a.prototype
		r.hwlen = a.hwlen
		r.protolen = a.protolen
		r.opcode = arp.REPLY
		r.hwdst = a.hwsrc
		r.protodst = a.protosrc
		r.protosrc = a.protodst
		mac = EthAddr(ip_to_mac(a.protodst.toStr()))
		r.hwsrc = mac

		e = ethernet(type=packet.type, src=mac, dst=a.hwsrc)
		e.payload = r
		msg = of.ofp_packet_out()
		msg.data = e.pack()
		msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
		msg.in_port = event.port
		event.connection.send(msg)

		return EventHalt

def launch():
	core.registerNew(arp_responder)