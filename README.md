# CS 252 Final Project - Fat Tree Topology in Mininet and POX

This repo contains an implementation of the fat-tree data center topology as described in [A Scalable, Commodity Data Center Network Architecture](http://ccr.sigcomm.org/online/files/p63-alfares.pdf) by Al-Fares et. al.

It uses Mininet to construct the fat-tree topology and implements two different routing algorithms using the POX openflow controller. The fat-tree Mininet topology is constructed in [topo_ft.py](topo_ft.py). The routing algorithms are simple dijkstra shortest-path routing and the specialized two-level routing scheme described in the paper. The openflow controllers for these are contained in [controller_dj.py](controller_dj.py) and [controller_2level.py](controller_2level.py).

Install this project by cloning this repo onto a mininet vm and symlinking topo_ft.py, controller_dj.py, controller_2level.py and fakearp.py to ~/pox/ext. Run it with `sudo ./run_net.py controller [--iperf]` where controller is either 'dijkstra' or '2level'. Include the '--iperf' flag to run an iperf-based performance test, measuring average throughput for a number of different traffic patterns as described the by files in the [inputs](inputs) folder.
