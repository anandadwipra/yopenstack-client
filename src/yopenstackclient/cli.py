from openstackclient.shell import main as openstackmain
from yopenstackclient.ping_servers import start as start_ping
from yopenstackclient.network_router import start as start_network_souter
from yopenstackclient.server_find import start as start_server_find
import sys


def main():
    if sys.argv[1] == "ping":
        start_ping(sys.argv[1:])
    # elif sys.argv[1] == "network" and sys.argv[2] == "simple":
    #     start_network_simple(sys.argv[2:])
    elif sys.argv[1] == "network" and sys.argv[2] == "router":
        start_network_souter(sys.argv[2:])
    elif sys.argv[1] == "server" and sys.argv[2] == "find":
        start_server_find()
    else:
        openstackmain()
    sys.exit()
