import json
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import jenkins
import pprint
import xmltodict
from urllib.parse import urlencode, quote_plus, urlparse
from database import Database
from utils import Utils
import argparse
from bs4 import BeautifulSoup
import cryptography
import re


utils = Utils()
DB = Database(False, 'localhost')

jenkins_url = DB.creds['jenkins_url']
basic = None


class JenkinsException(Exception):
    '''General exception type for jenkins-API-related failures.'''
    pass


def get_server_instance(args):
    server = jenkins.Jenkins(jenkins_url, username=args.usr, password=args.tok)
    return server


def get_projects(server):
    projects = []
    for ji in server.get_all_jobs(folder_depth=None):
        projects.append(ji)
    return projects


def get_queue_lengths(server):
    queue_length = {}
    queue_info = server.get_queue_info()
    pprint.pprint(queue_info)
    if queue_info:
        queue_length['length'] = len(queue_info)
        queue_length['data'] = queue_info

    return queue_length


def get_node_name(server, basic, url):
    wsurl = url+"ws"
    page = requests.get(wsurl, auth=basic)
    soup = BeautifulSoup(page.content, "html.parser")
    ahref = soup.find_all("a", class_="model-link inside")
    if len(ahref) < 1:
        ###qrybuild = "{h}/api/json?tree=id,timestamp,builtOn&pretty=true".format(h=url)
        qrybuild = "{h}/api/json?pretty=true".format(h=url)
        qbpage = requests.get(qrybuild, auth=basic)
        qbjson = json.loads(qbpage.content)
        if 'builtOn' in qbjson.keys():
            node_name = qbjson['builtOn']
        else:
            node_name = parse_build_log_for_nodename(url)
            node_name = "{n}_{i}".format(n=node_name[0],i=node_name[1])
    else:
        node_name = ahref[-1].text
    return node_name


def get_limited_request_data(url, limit):
    r = requests.get(url, auth=basic, stream=True, timeout=10)
    rcontent = ''
    for chunk in r.iter_content(1024):
        if len(chunk)> limit:
            rcontent += str(chunk.decode("utf-8"))
            r.close()
        else:
            rcontent += str(chunk.decode("utf-8"))
            r.close()
            break
    return rcontent


def parse_build_log_for_nodename(url):
    url = '{u}/consoleText'.format(u=url)
    page = get_limited_request_data(url, 8192)
    text = [ x for x in str(page).splitlines() if "Running on" in x]
    if text and len(text[0]) > 3:
        text = text[0].split(' ')
        if len(text) > 4:
            return(text[3],text[4])  # ec2 fleets generate a name with a space in it, left side is useless info, right side is node
    return 'no node assigned',''

def get_all_builds(server, basic):
    projects = []
    all_builds = []
    for ji in server.get_all_jobs(folder_depth=None):
        if 'jobs' in ji.keys():
            for job in ji['jobs']:
                if 'folder' in job['_class'] or 'Maintennance' in job['url']:
                    print("\tprocessing job folder")
                    continue
                try:
                    print("{j}".format(j=job['fullname']))
                    info = server.get_job_info(job['fullname'])
                    if 'builds' not in info.keys():
                        print("\tNo builds")
                        continue
                    builds_info = info['builds']
                    for build in builds_info:
                        # print("\t{b}".format(b=build['number']))
                        build_info = server.get_build_info(job['fullname'], build['number'], depth=2)
                        timestamp = datetime.utcfromtimestamp(build_info['timestamp']/1e3)
                        build_info['timestamp'] = str(timestamp)
                        executor_data = get_node_name(server, basic, build_info['url'])
                        try:
                            DB.Exec_Insert_build(displayname=build_info['fullDisplayName'],
                                                 timestamp=timestamp,
                                                 duration=build_info['duration'],
                                                 executor=executor_data,
                                                 url=build_info['url'])
                        except Exception as e:
                            pprint.pprint(e)
                            pprint.pprint({'displayname': build_info['fullDisplayName'],
                                           'timestamp': timestamp,
                                           'duration': build_info['duration'],
                                           'executor': executor_data,
                                           'url': build_info['url']})
                            exit(1)
                        all_builds.append(build_info)
                except Exception as e:
                    print("get_all_builds exception:")
                    print(job)
                    print("--")
                    pprint.pprint(e)
                    continue
                pass
    return all_builds


def get_build_data(server, basic):
    builds = get_all_builds(server, basic)
    for build in builds:
        f.write(
            "{dn},{ts},{d},{e}\n".format(dn=build['fullDisplayName'], ts=build['timestamp'], d=build['duration'],
                                         e=get_node_name(server, basic, build['url'])))
        # pprint.pprint(build)


def get_executing_builds(server):
    # print("get_running_builds fails right now on the built in instance")
    # exit(1)
    all_builds = get_running_builds(server)
    return all_builds


def get_running_builds(server):
    '''Return list of running builds.

    Each build is a dict with keys 'name', 'number', 'url', 'node',
    and 'executor'.

    :returns: List of builds,
      ``[ { str: str, str: int, str:str, str: str, str: int} ]``

    Example::
        >>> builds = server.get_running_builds()
        >>> print(builds)
        [{'node': 'foo-slave', 'url': 'https://localhost/job/test/15/',
          'executor': 0, 'name': 'test', 'number': 15}]
    '''
    builds = []
    nodes = server.get_nodes()
    for node in nodes:
        # the name returned is not the name to lookup when
        # dealing with master :/
        if node['name'] == 'master':
            node_name = '(master)'
        else:
            node_name = node['name']
        if 'built-in' not in node_name.lower():
            if ' ' in node_name: # account for ec2 fleet node names - only needs part after space
                node_name = node_name.split(' ')[1]
            try:
                info = server.get_node_info(node_name, depth=2)
            except JenkinsException as e:
                # Jenkins may 500 on depth >0. If the node info comes back
                # at depth 0 treat it as a node not running any jobs.
                if ('[500]' in str(e) and
                        server.get_node_info(node_name, depth=0)):
                    continue
                else:
                    raise
        else:
            continue
        for executor in info['executors']:
            executable = executor['currentExecutable']
            if executable and 'number' in executable:
                executor_number = executor['number']
                build_number = executable['number']
                url = executable['url']
                m = re.search(r'/job/([^/]+)/.*', urlparse(url).path)
                job_name = m.group(1)
                builds.append({'name': job_name,
                               'number': build_number,
                               'url': url,
                               'node': node_name,
                               'executor': executor_number})
    return builds


def get_project_data(server):
    projects = get_projects(server)
    #for proj in projects:
    #    pprint.pprint(proj)


def get_nodes(server, basic):
    nodes = server.get_nodes()
    for node in nodes:
        name = node['name']
        if ' ' in name:
            name = name.split(' ')[1]
        if server.node_exists(name):
            node_info = server.get_node_info(name)
            node_config = xmltodict.parse(server.get_node_config(name))  # this call requires auth
            node['node_info'] = node_info
            node['node_config'] = node_config
            log_url = "{su}/computer/{n}/log".format(su=jenkins_url, n=name)
            result = requests.get(log_url, auth=basic)
            pass
        else:
            # print("Node {n} doesn't exist".format(n=name))
            continue
    return nodes


def get_args():
    parser = argparse.ArgumentParser("Jenkins data mining")
    parser.add_argument('-usr', required=True, help='Jenkins user name')
    parser.add_argument('-tok', required=True, help='Jenkins user token')
    parser.add_argument('-gpd', default=False, action='store_true',
                        help='Get Project data')
    parser.add_argument('-gab', default=False, action='store_true',
                        help='Get all builds')
    parser.add_argument('-nod', default=False, action='store_true',
                        help='Get nodes')
    parser.add_argument('-geb', default=False, action='store_true',
                        help='Get executing builds')
    parser.add_argument('-gq', default=False, action='store_true',
                        help='Get queue data')
    return parser.parse_args()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    args = get_args()
    server = get_server_instance(args)
    basic = HTTPBasicAuth(args.usr, args.tok)

    if args.gq:
        queue_lengths = get_queue_lengths(server)
    # ------------------------------------------------
    if args.gpd:
        get_project_data(server)
    # ------------------------------------------------
    if args.gab:
        all_builds = get_all_builds(server, basic)
        with open("all_builds.json", "w") as f:
            json.dump(all_builds, f, indent=4)
    # ------------------------------------------------
    if args.geb:
        building = get_executing_builds(server)
        with open("building.json", "w") as f:
            json.dump(building, f, indent=4)
    # ------------------------------------------------
    if args.nod:
        nodes = get_nodes(server, basic)
        with open("nodes.json", "w") as f:
            json.dump(nodes, f, indent=4)
