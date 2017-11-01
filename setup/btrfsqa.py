import json
import time
import os
import boto.ec2

from fabric.context_managers import settings
from fabric.api import *
from fabric.contrib.files import exists

# aws,github credentials
AUTH_FILE_PATH = "./config/aws_auth.json"
CONFIG_FILE_PATH = "./config/ec2.json"
GITHUB_FILE_PATH = "./config/github.json"
TIMEOUT_FILE_PATH = "./config/timeout.json"
SLEEP_TIME = 5
RETRY = 25  # retry times if connection fails.
RETRY_DELAY = 3  # delay between retry attempts in seconds
ASCIINEMA_REC = "asciinema rec -w 2.5 "

TABLE_DATE = "<h3>Test Results: ["+time.strftime('%d-%m-%Y')+"] </h3>"
TABLE_HEADER = "<table> <thead> <tr>\
<th style='text-align: left'>Script</th> \
<th style='text-align: left'>Status</th> \
<th style='text-align: left'>Watch</th>  \
<th style='text-align: left'>Logs</th>   \
</tr> </thead><tbody>"
TABLE_FOOTER = "</tbody> </table>"

# git commands
set_gitname = "git config --global user.name "
set_gitmail = "git config --global user.email "
gitpush = " git push -u origin master "
gitadd = "cd ~/btrfsqa && git add . "

# fill aws details
j_fd = open(AUTH_FILE_PATH)
aws_config = json.load(j_fd)
j_fd.close()

# Fab file entries
env.key_filename = aws_config['pem_file']
env.user = 'fedora'
env.hosts = []

# Load instance config from json file
j_fd = open(CONFIG_FILE_PATH)
config = json.load(j_fd)
j_fd.close()

# Load instance config from json file
j_fd = open(GITHUB_FILE_PATH)
github = json.load(j_fd)
j_fd.close()

# Load script timeout details
j_fd = open(TIMEOUT_FILE_PATH)
time_conf = json.load(j_fd)
j_fd.close()


def ec2_connect():
    # Open EC2 connection
    ec2_conn = boto.ec2.connect_to_region(
                    aws_config['region'],
                    aws_access_key_id=aws_config['key'],
                    aws_secret_access_key=aws_config['secret'])
    return ec2_conn


def req_instance_and_tag(ec2_conn):

    # Configure block device mapping
    if 'block-device-mapping' in config:
        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        for name, bd in config['block-device-mapping'].iteritems():
            bdm[name] = boto.ec2.blockdevicemapping.BlockDeviceType(**bd)
    else:
        bdm = None

    # Request spot instance
    spot_req = ec2_conn.request_spot_instances(block_device_map=bdm,
                                               **config['spot-request'])[0]

    # Tag the request, once we can get a valid request ID.
    print('Tagging spot request.')
    while True:
        try:
            ec2_conn.create_tags(spot_req.id, config['tags'])
        except:
            pass
        else:
            break

    # Wait while the spot request remains open
    state = 'open'
    while state == 'open':
        time.sleep(SLEEP_TIME)
        spot = ec2_conn.get_all_spot_instance_requests(spot_req.id)[0]
        state = spot.state
        print('Spot request ' + spot.id + ' status: ' + spot.status.code
              + ': ' + spot.status.message)

    # Exit if there is an error
    if (state != 'active'):
        exit(1)
    return spot, bdm


def set_bdm(spot, bdm, ec2_conn):
    # Get the instance and wait until block devs attached to it.
    bd_count = 0
    ids_to_tag = []
    while bd_count < len(bdm):
        time.sleep(4)
        instance = ec2_conn.get_only_instances(spot.instance_id)[0]
        bd_count = len(instance.block_device_mapping)

    # Get block devices to tag
    for bd in instance.block_device_mapping.itervalues():
        ids_to_tag.append(bd.volume_id)

    # Tag resources
    print('Tagging instance and attached volumes.')
    ec2_conn.create_tags(ids_to_tag, config['tags'])
    instance = ec2_conn.get_only_instances(spot.instance_id)[0]

    # Wait till instance is out of pending state
    while instance.state == 'pending':
        time.sleep(SLEEP_TIME)
        instance = ec2_conn.get_only_instances(spot.instance_id)[0]
        print('Instance ' + instance.id + ' state: ' + instance.state)
    return instance


def install_sw(instance):
    #  fab setup
    env.hosts.append(instance.ip_address)
    connected = False

    #  Test connection
    for x in range(RETRY):
        try:
            with settings(host_string=env.user + '@' + instance.ip_address):
                print("Testing connection for instance:" + str(instance.id)
                      + " ip:" + str(instance.ip_address))
                run("ls /tmp")
                run("mkdir -p /tmp/logs ")
                connected = True
                break
        except:
            time.sleep(RETRY_DELAY)
        else:
            break

    if connected is True:
        try:
            with settings(host_string=env.user + '@' + instance.ip_address):
                run("ls /tmp && mkdir ~/btrfsqe ")
                print("Uploading config files")
                put("./config/bashrc", "~/btrfsqe/bashrc")
                put("./config/local.config", "~/btrfsqe/local.config")
                put("./config/kernel.config", "~/btrfsqe/kernel.config")
                put("./config/timeout.json", "~/btrfsqe/timeout.json")
                run("sudo cp -v ~/btrfsqe/bashrc /etc/")
                sudo("yum -y install git python34 asciinema")
                print("Uploading scripts")
                scripts = os.listdir('./scripts')
                scripts.sort()
                for f in scripts:
                    put("./scripts/" + f, "~/btrfsqe/" + f)
                for f in scripts:
                    cmd = "timeout " + time_conf[f] + "m sh ~/btrfsqe/" + f
                    run(ASCIINEMA_REC+" ~/btrfsqe/"+f+".cast -c '"+cmd+"'")
                    run("sleep 5")
                    if exists('~/btrfsqe/001_btrfsdevel.completed'):
                        run('mv ~/btrfsqe/001_btrfsdevel.completed ~/btrfsqe/001_btrfsdevel.rebooting')
                        with settings(hide('warnings'), warn_only=True,):
                            reboot(wait=60)  # Please come back :-)
                            run("sleep 120")
                            run("uname -a")
                            run('mv ~/btrfsqe/001_btrfsdevel.rebooting ~/btrfsqe/001_btrfsdevel.ok')
                    else:
                        with settings(hide('warnings'), warn_only=True, ):
                            run("mv ~/btrfsqe/" + f + ".completed ~/btrfsqe/" + f + ".ok")
                urls = {}
                test_status = {}
                for f in scripts:
                    with settings(hide('warnings'), warn_only=True, ):
                        output = run('asciinema upload ~/btrfsqe/'+f+'.cast')
                    urls[f] = output
                    if exists('~/btrfsqe/' + f + '.ok'):
                        test_status[f] = "pass"
                    else:
                        test_status[f] = "fail"
                # move test logs
                results = time.strftime("%Y-%m-%d_%H:%M")
                results_dir = "~/btrfsqe/results_" + results
                run('mkdir -p ' + results_dir)
                xfstests_results = results_dir + "/xfstests_" + results
                btrfsprogs_results = results_dir + "/btrfsprogs_" + results
                run('mkdir -p ' + xfstests_results)
                run('mkdir -p ' + btrfsprogs_results)
                with settings(hide('warnings'), warn_only=True, ):
                    run("cp -r ~/btrfs-progs/tests/*tests-results.txt " + btrfsprogs_results)
                    run("cp -r ~/xfstests/results " + xfstests_results)
                # prepare html entries with status
                table_block = ""
                col = "</td><td>"
                for k, v in test_status.items():
                    vformat = " width='128' height='100' class='img-rounded' "
                    vlink = "<a href=" + urls[k] + " target='_blank'>"
                    vlink = vlink + "<img src=" + urls[k] + ".png"
                    vlink = vlink + vformat + "/></a>"
                    status = "<code class='highlighter-rouge'>" + v + "</code>"
                    logurl = "<a href=" + github['repo_url']
                    logurl = logurl + "/results_" + results + ">logs</a>"
                    table_block = table_block + "<tr><td>" + k + col
                    table_block = table_block + status + col
                    table_block = table_block + vlink + col
                    table_block = table_block + logurl + "</td></tr>"
                # prepare github
                run(set_gitname + github['committer'])
                run(set_gitmail + github['commit_email'])
                put("./config/netrc", "~/.netrc")
                run("git clone " + github['repo'])
                run("cp -r " + results_dir + " ~/btrfsqa/results")
                run(gitadd + " && git commit -m 'logs' &&" + gitpush)
                update_htmltable(table_block)
                run(gitadd + " && git commit -m 'html' && " + gitpush)
                run("shred ~/.netrc")
        except Exception as e:
            print("*" * 10 + "ERROR:" + str(e) + "*" * 10)
    else:
        print("*" * 10 + "Connection failed. Abort")


def update_htmltable(table_block):
    filepath = "~/btrfsqa/_layouts/default.html"
    localpath = "/tmp/default.html"
    get(filepath, localpath)
    with open(localpath, 'r') as fd:
        filedata = fd.read()
    new_table = TABLE_DATE + TABLE_HEADER + table_block + TABLE_FOOTER
    filedata = filedata.replace("hearts;", "hearts;"+new_table)
    with open(localpath, 'w') as fd:
        fd.write(filedata)
    put(localpath, filepath)


def del_sys(instance, ec2_conn):
    print("In 2 minutes: Deleting instance in \
           which as has ip:" + str(instance.id) + str(instance.ip_address))
    time.sleep(120)
    ec2_conn.terminate_instances(instance.id)
    print("Delete and Free volumes")
    my_all_vol = ec2_conn.get_all_volumes()
    for v in my_all_vol:
        print (v.id + v.status)
        if v.status == "available":
            print ("Deleting Volume" + v.id)
            ec2_conn.delete_volume(v.id)


def main():
    ec2_conn = ec2_connect()
    spot, bdm = req_instance_and_tag(ec2_conn)
    instance = set_bdm(spot, bdm, ec2_conn)
    install_sw(instance)
    ec2_conn = ec2_connect()
    del_sys(instance, ec2_conn)


if __name__ == '__main__':
    main()
