#!/usr/bin/env python

from topo_ft import FatTreeTopo

from mininet.node import RemoteController
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info, warn, error, debug
from mininet.clean import cleanup

from subprocess import Popen, PIPE
import os
import sys
import atexit
import signal
import glob
from time import sleep

K = 4

CONTROLLERS = {
	'2level': 'controller_2level',
	'dijkstra': 'controller_dj'
}

# prints numbers with a nice SI prefix attached
# taken from https://stackoverflow.com/a/1094933
def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.4f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.4f %s%s" % (num, 'Yi', suffix)

# find the mean of a list
def list_mean(list):
	return sum(list) / float(len(list))

# find the standard deviation of a list
def list_stdev(list):
	mean = list_mean(list)
	sq_diff = [(x - mean) ** 2 for x in list]
	return list_mean(sq_diff) ** 0.5

# print mean and standard deviation for a file given list of throughput results
def print_stats(filename, results):
	avg = sum(results) / float(len(results))
	stdev = list_stdev(results)
	print '%s:'%filename
	print '\tthroughput mean: %s'%sizeof_fmt(avg, suffix='bits/sec')
	print '\tthroughput standard deviation: %s'%sizeof_fmt(stdev, suffix='bits/sec')
	print

# run iperf test as specified by input file with name input_filname
def run_iperf(net, input_filename):
	flows = []
	with open(input_filename) as infile:
		for line in infile:
			if line.startswith('#'):
				continue
			fields = line.split(' ')
			flow = {}
			flow['srcip'] = fields[0]
			flow['dstip'] = fields[1]
			flows.append(flow)
	
	server_procs = []
	for host in net.hosts:
		if any(d['dstip'] == host.IP() for d in flows):
			p = host.popen(['/usr/bin/iperf', '-s'])
			server_procs.append(p)
	
	hosts_by_ip = {h.IP():h for h in net.hosts}
	client_procs = []
	for flow in flows:
		host = hosts_by_ip[flow['srcip']]
		p =  host.popen(['/usr/bin/iperf',
			'-yc',
			'-c', flow['dstip']
		], stdout=PIPE)

		client_procs.append(p)

	results = []
	for p in client_procs:
		p.wait()
		iperf_output = p.communicate()[0].split(',')
		results.append(int(iperf_output[8]))
	
	for p in server_procs:
		p.kill()
	
	print_stats(input_filename, results)

def run_pox(controller_name):
	controller = CONTROLLERS[controller_name]
	p_pox = Popen(
		[os.environ['HOME'] + '/pox/pox.py', 'fakearp', controller, '--topo=fattree,%d'%K, '--install'],
		# make pox ignore sigint so we can ctrl-c mininet stuff without killing pox
		preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
	)
	atexit.register(p_pox.kill)

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print 'usage: sudo ./run_net.py controller [--iperf]'
		sys.exit()

	controller_name = sys.argv[1]
	if controller_name not in CONTROLLERS:
		print 'controller must be one of these:', ', '.join(CONTROLLERS.keys())
		sys.exit()
	
	use_iperf = len(sys.argv) > 2 and sys.argv[2] == '--iperf'

	atexit.register(cleanup)
	# just in case program gets interrupted before iperfs get killed
	atexit.register(lambda: os.system('killall iperf 2> /dev/null'))

	run_pox(controller_name)

	# wait for pox to come up
	sleep(1)

	topo = FatTreeTopo(K)
	net = Mininet(topo, controller=RemoteController)
	net.start()

	# wait for switches to connect to controller
	sleep(3)

	if use_iperf:
		print 'running iperf test'
		print 'using controller ', controller_name
		print
		for infile in sorted(glob.glob('inputs/*')):
			run_iperf(net, infile)
	else:
		CLI(net)
