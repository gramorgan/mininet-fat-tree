'''
based on riplpox 
'''

import sys
sys.path.append(".")

from mininet.topo import Topo
from mininet.node import Controller, RemoteController, OVSKernelSwitch, CPULimitedHost
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.util import custom
from mininet.log import setLogLevel, info, warn, error, debug

from DCTopo import FatTreeTopo
from DCRouting import Routing

from subprocess import Popen, PIPE
from argparse import ArgumentParser
import multiprocessing
from time import sleep
from monitor.monitor import monitor_devs_ng
import os


# Number of pods in Fat-Tree 
K = 4

# Queue Size
QUEUE_SIZE = 100

# Link capacity (Mbps)
BW = 10 

parser = ArgumentParser(description="minient_fattree")

parser.add_argument('-d', '--dir', dest='output_dir', default='log',
        help='Output directory')

parser.add_argument('-i', '--input', dest='input_file',
        default='inputs/all_to_all_data',
        help='Traffic generator input file')

parser.add_argument('-t', '--time', dest='time', type=int, default=30,
        help='Duration (sec) to run the experiment')

parser.add_argument('-p', '--cpu', dest='cpu', type=float, default=-1,
        help='cpu fraction to allocate to each host')

parser.add_argument('--iperf', dest='iperf', default=False, action='store_true',
        help='Use iperf to generate traffics')

parser.add_argument('--ecmp',dest='ECMP',default=False,
        action='store_true',help='Run the experiment with ECMP routing')

parser.add_argument('--tlr',dest='tlr', default=False,
        action='store_true', help='Run the experiment with Fat-Tree two-level routing')

parser.add_argument('--dijkstra',dest='dij',default=False,
        action='store_true',help='Run the experiment with dijkstra routing')

args = parser.parse_args()



def FatTreeNet(args, k=4, bw=10, cpu=-1, queue=100, controller='DCController'):
    ''' Create a Fat-Tree network '''

    if args.ECMP:
        pox_c = Popen("~/pox/pox.py %s --topo=ft,4 --routing=ECMP"%controller, shell=True)
    elif args.dij:
        pox_c = Popen("~/pox/pox.py %s --topo=ft,4 --routing=dij"%controller, shell=True)
    else:
        info('**error** the routing scheme should be ecmp or dijkstra\n')


    info('*** Creating the topology')
    topo = FatTreeTopo(k)

    host = custom(CPULimitedHost, cpu=cpu)
    link = custom(TCLink, bw=bw, max_queue_size=queue)
    
    net = Mininet(topo, host=host, link=link, switch=OVSKernelSwitch,
            controller=RemoteController)

    return net

def install_proactive(net, topo):
    """
        Install proactive flow entries for switches.
    """
    pass


def iperfTrafficGen(args, hosts, net):
    ''' 
    Generate traffic pattern using iperf and monitor all of the interface
    '''
    pass


def FatTreeTest(args,controller):
    net = FatTreeNet(args, k=K, cpu=args.cpu, bw=BW, queue=QUEUE_SIZE,
            controller=controller)
    net.start()

    '''
    uncomment and implement the following fucntion if flow tables are installed proactively, 
    in this mode, the mininet can work without a controller
    '''
    # install_proactive(net, topo)


    # wait for the switches to connect to the controller
    info('** Waiting for switches to connect to the controller\n')
    sleep(5)

    hosts = net.hosts
    
    iperfTrafficGen(args, hosts, net)

    net.stop()

def clean():
    ''' Clean any the running instances of POX '''

    p = Popen("ps aux | grep 'pox' | awk '{print $2}'",
            stdout=PIPE, shell=True)
    p.wait()
    procs = (p.communicate()[0]).split('\n')
    for pid in procs:
        try:
            pid = int(pid)
            Popen('kill %d' % pid, shell=True).wait()
        except:
            pass

if __name__ == '__main__':

    setLogLevel( 'info' )
    if not os.path.exists(args.output_dir):
        print args.output_dir
        os.makedirs(args.output_dir)

    clean()

    if args.ECMP:
        FatTreeTest(args,controller='DCController')
    elif args.dij:
        FatTreeTest(args,controller='DCController')
    elif args.tlr:
        #flow tables in two-level routing are installed proactively, so no need of controller
        FatTreeTest(args,controller= None) 
    else:
        info('**error** please specify either ecmp, dijkstra or tlr\n')
        
    clean()

    Popen("killall -9 top bwm-ng", shell=True).wait()
    os.system('sudo mn -c')
