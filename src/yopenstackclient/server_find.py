#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
from re import findall
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client
from yaml import load, SafeLoader
from rich.console import Console
from rich.table import Table
from datetime import datetime
import pickle
import os
from neutronclient.v2_0 import client as nclient
import argparse


def auth(site, config):
    with open(config, 'r') as f:
        credential = load(f, Loader=SafeLoader)
    cacert = credential["clouds"][site]["cacert"]
    credential = credential["clouds"][site]["auth"]

    auth = v3.Password(
            auth_url=credential["auth_url"],
            username=credential["username"],
            password=credential["password"],
            project_id=credential["project_id"],
            project_name=credential["project_name"],
            user_domain_name=credential["user_domain_name"],
            project_domain_id=credential["project_domain_id"]
            )
    return session.Session(auth=auth, verify=cacert)


def printTable(compute, server_lists, instance_name):
    table = Table(title=compute)
    table.add_column("Id", justify='left', style="cyan")
    if instance_name:
        table.add_column("InstanceID", justify='left', style='bright_green')
    table.add_column("Name", justify='left', style='bright_green')
    table.add_column("Internal IP", justify='right', style='bright_green')
    table.add_column("Floating IP", justify='right', style='bright_green')
    table.add_column("Flavor", justify='center', style='bright_green')
    table.add_column("Host", justify='center', style='bright_green')

    for row in server_lists:
        try:
            table.add_row(*row)
        except Exception:
            print(row)

    console = Console()
    console.print(table)


def storeCache(filename, vms, flav, external_net):
    db = {}
    db["vms"] = vms
    db["flavor"] = flav
    db["network"] = external_net
    # store cache
    dbfile = open(filename, "wb")
    pickle.dump(db, dbfile)
    print("Caching")
    dbfile.close()


def loadCache(filename):
    dbfile = open(filename, "rb")
    db = pickle.load(dbfile)
    print("load data")
    dbfile.close()
    return db


def refreshCache(site, filename, config):
    nova = client.Client(2, session=auth(site, config))
    marker=None
    vms_raw = nova.servers.list(detailed=True, search_opts={"all_tenants": True},marker=marker)
    if len(vms_raw) % 1000 == 0:
        marker = vms_raw[-1].id
        vms_raw += nova.servers.list(detailed=True, search_opts={"all_tenants": True},marker=marker)
    vms = []
    vm = {}
    vms_field = ["id","OS-EXT-SRV-ATTR:instance_name", "name", "addresses", "flavor", "OS-EXT-SRV-ATTR:hypervisor_hostname"]
    # List all VMs
    for vm_raw in vms_raw:
        vm_raw = vm_raw.to_dict()
        for vm_field in vms_field:
            if vm_field == "addresses" and len(vm_raw["addresses"]) == 0:
                vm[vm_field] = {"NoNetworkAttached": [{"addr": "0"}]}
            else:
                vm[vm_field] = vm_raw[vm_field]
        vms.append(vm)
        vm = {}
    # List all Flavors
    flavors_raw = nova.flavors.list(is_public=None)
    flavors = {}
    for flavor_raw in flavors_raw:
        flavors[flavor_raw.to_dict()["id"]] = flavor_raw.to_dict()["name"]
    # List all external Networ
    filter_params = {"router:external": True}
    external_net = []
    neutron = nclient.Client(session=auth(site, config))
    for network in neutron.list_networks(retrieve_all=True, **filter_params)["networks"]:
        external_net.append(network["name"])

    # Store Cache to file
    print("scraping data")
    storeCache(filename, vms, flavors, external_net)


def sortir(e):
    return e[2] if len(e) == 7 else e[1]


def search(sites, **kwargs):
    if kwargs['cdate'] is None:
        date = datetime.now().strftime("%d%m%Y")
    else:
        date = kwargs['cdate']
    filename = "bsdcache" if sites == "jkt" else "sbycache"
    filename = "/home/dev/openstack/pycache2/"+filename+date
    if not os.path.isfile(filename) or kwargs["refresh"]: refreshCache(sites, filename, kwargs["config"])
    cache = loadCache(filename)
    datasvm = cache["vms"]
    flavor = cache["flavor"]
    external_net = cache["network"]
    row = []
    rows = []
    sites = "BSD CLOUD" if sites == "jkt" else "SBY CLOUD"
    for datavm in datasvm:
        vm_ip = ",".join([item['addr'] for item in list(datavm["addresses"].values())[0]])

        if kwargs["hint"] in datavm["name"] or kwargs["hint"] in vm_ip:
            for field in datavm:
                if field == "flavor":
                    row.append(flavor[datavm[field]["id"]])
                elif field == "addresses":
                    for x in datavm[field]:
                        if len(datavm[field][x]) == 2:
                            row.append(str(datavm[field][x][0]["addr"]))
                            row.append(str(datavm[field][x][1]["addr"]))
                            break
                        elif datavm[field][x] == list(datavm[field].values())[-1] and str(datavm[field][x][0]["addr"]) == "0":
                            row.append("-")
                            row.append("-")
                            break
                        elif datavm[field][x] == list(datavm[field].values())[-1]:
                            # if x in external_net:
                            if findall(r'10\.[0-9]?[0-9](?:\.[0-9]+){2}', datavm[field][x][0]["addr"]):
                                row.append("-")
                                row.append(str(datavm[field][x][0]["addr"]))
                            else:
                                row.append(str(datavm[field][x][0]["addr"]))
                                row.append("-")
                elif not kwargs["instance_name"] and field == "OS-EXT-SRV-ATTR:instance_name":
                    continue
                else:
                    row.append(datavm[field])
            rows.append(row)
            row = []
    rows.sort(key=sortir)
    # print(rows)
    printTable(sites, rows, kwargs["instance_name"])


def start():
    parser = argparse.ArgumentParser()
    parser.add_argument('arg1', help=argparse.SUPPRESS)
    parser.add_argument('arg2', help=argparse.SUPPRESS)
    parser.add_argument("hint", help="Hints for finding a server")
    parser.add_argument("-i", "--instance-name", help="Show instance name", action="store_true")
    parser.add_argument("--refresh", help="Refresh Cache", action="store_true")
    parser.add_argument("--sby", help="Show Only SBY Site", action="store_true")
    parser.add_argument("--bsd", help="Show Only BSD Site", action="store_true")
    parser.add_argument("-C", "--column", help="specify the column(s) to include, can be repeated to show multiple columns", action="append")
    parser.add_argument('-c', '--config-file', help="Import cloud config", required=True)
    parser.add_argument('-d', '--cache-date', help="Specify cache date",action="store")
    args = parser.parse_args()
    params = {
            "instance_name": args.instance_name,
            "hint": args.hint,
            "refresh": args.refresh,
            "config": args.config_file,
            "cdate": args.cache_date
            }

    # print(args.column)
    # sys.exit()
    # if len(arg) <= 1:
        # print("Usage: openstack server find --help")
    if args.sby:
        search("sby", **params)
    elif args.bsd:
        search("jkt", **params)
    else:
        search("sby", **params)
        search("jkt", **params)

    sys.exit()


# start()
