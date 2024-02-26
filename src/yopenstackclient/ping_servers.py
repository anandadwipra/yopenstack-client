#!/usr/bin/python
# -*- coding: utf-8 -*-
import subprocess
from re import findall, match
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client
from yaml import load, SafeLoader
from json import dumps
from rich.console import Console
from rich.table import Table
import time
from datetime import datetime
import sys
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


def printTable(compute, server_lists):
    table = Table(title=compute)
    table.add_column("Instance", justify='left', style="cyan")
    table.add_column("Networks", justify='left', style='bright_green')
    table.add_column("Floating IP", justify='right', style='bright_green')
    table.add_column("Ping", justify='center', style='bright_green')

    for row in server_lists:
        table.add_row(*row)

    console = Console()
    console.print(table)


def test_locals(compute):
    report_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    console = Console()
    console.log(
        log_locals=True,
    )


def start(arg):
    parser = argparse.ArgumentParser()
    parser.add_argument('arg1', help=argparse.SUPPRESS)
    parser.add_argument("compute", help="Compute name")
    parser.add_argument('-c', '--config-file', help="Import cloud config", required=True)
    args = parser.parse_args()
    # record start time
    start = time.time()

    if len(arg) <= 1:
        print("Usage: openstack ping --help")

    server_lists = []
    # get compute
    compute = args.compute

    # get site
    site = match(r'sf-(jkt|sby)', compute).group(1).strip()
    nova = client.Client(2, session=auth(site, args.config_file))
    server_lists_raw = nova.servers.list(detailed=True, search_opts={
        "host": compute,
        "all_tenants": "true"})

    for i in server_lists_raw:
        server = []
        server.append(i.name)
        result = dumps(i.networks).replace('{', '').replace('}', '').replace('"', '').replace('[', '').replace(']', '')
        server.append(result)
        floatingIP = findall(r'10\.[0-9]?[0-9](?:\.[0-9]+){2}', result)
        if len(floatingIP) == 0:
            server.append("Null")
        else:
            server.append(floatingIP[0])
        server_lists.append(server)

    for server in server_lists:
        if server[2] != "Null":
            response = subprocess.run(
                    args=["ping", "-W", "2", "-c", "1", server[2]],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    ).returncode
            if response == 0:
                server.append("Alive")
            else:
                server.append("Timeout")
        else:
            server.append("-")

    printTable(compute, server_lists)
    end = time.time()
    print("The time of execution of above program is :", (end-start) * 10**3, "ms")

    test_locals(compute)
