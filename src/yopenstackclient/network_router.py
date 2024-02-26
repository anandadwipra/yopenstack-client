#!/usr/bin/python3
import openstack, sys, os
from keystoneauth1.identity import v3
from keystoneauth1 import session
from neutronclient.v2_0 import client


def auth():

    auth = v3.Password(
            auth_url=os.environ["OS_AUTH_URL"],
            username=os.environ["OS_USERNAME"],
            password=os.environ["OS_PASSWORD"],
            project_id=os.environ["OS_PROJECT_ID"],
            project_name=os.environ["OS_PROJECT_NAME"],
            user_domain_name=os.environ["OS_USER_DOMAIN_NAME"],
            project_domain_id=os.environ["OS_PROJECT_DOMAIN_ID"]
            )

    return session.Session(auth=auth, verify=os.environ["OS_CACERT"])


def start(arg):
    if len(arg) <= 1:
        print("Usage: openstack ping --help")

    network = arg[1]
    sess = auth()
    # ks = client.Client(session=sess)
    # print(ks.users.list())
    neutron = client.Client(session=sess)
    network = neutron.list_networks(retrieve_all=True, name=network)
    network = network["networks"]
    if network[0]["router:external"]:
        print("Network Type\t: Eksternal")
        devices = neutron.list_ports(network_id=network[0]["id"],device_owner="network:router_gateway")["ports"]
        for device in devices:
            router = neutron.list_routers(id=device["device_id"])["routers"]
            print("Router Name\t:", router[0]["name"])
    else:
        print("Network Type\t: Internal")
        try:
            device_id = neutron.list_ports(network_id=network[0]["id"],device_owner="network:router_interface_distributed")["ports"][0]["device_id"]
        except IndexError:
            print("No router found")
            sys.exit()
        router = neutron.list_routers(id=device_id)["routers"][0]["name"]
        print("Router Name\t:", router)
