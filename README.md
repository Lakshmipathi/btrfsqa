BTRFSQA 
=======    
What it does?
============
It launches vm on cloud and installs btrfs-devel kernel and then runs btrfsprogs/xfstests-btrfs tests. Basic idea is to create BTRFS community driven test script and tools. Hopefully will be adding more user test scripts.

Once tests are completed it uploads the log into github repo along with asciinema screencasting. Then updates [BTRFSQA][1]  with ppropriate status and links.

[1]: http://lakshmipathi.github.io/btrfsqa/ 

Test machine details:
================
Linux Distro: Fedora-26 AWS EC2 instance.
Drives: Unformatted 6 devices available for use. They are from /dev/xvdb to /dev/xvdg. Each device has 20GB disk space.

How to add new scripts?
=======================
- Create a script under "scripts/" make sure its named appropriately.
- Edit "config/timeout.json" with appropriate timeout limit (in minutes) 
  for the script.(see man timeout)
- The script must create "script_name.completed" to indicate its success 
  under ~/btrfsqe
- Logs stored under /tmp/logs will be pushed into github.

Sample script: scripts/000_mkdir_test:
=============
```
  echo "Testing mkdir"
  sudo mkfs.btrfs /dev/xvdb
  sudo mount /dev/xdb /mnt
  sudo mkdir -v /mnt/testdir &> /tmp/logs/mkdir.log
  #indicate script completed.
  touch ~/btrfsqe/000_mkdir_test.completed  
  ```

Using your Github/AWS accounts:
==============================
If you prefer to setup this script inside your org. using your account. 
Ensure host machine has python-fabric and boto installed. Then you need to:

 - Place your aws .pem file under config and then edit setup/config/aws_auth.json 
    with your AWS credentials.
 - Edit setup/config/netrc and github.json with your github credentials.
  Optionally, edit setup/config/ec2.json if you like to use different EC2 instance.
 

Author:
======
Feel free to ping me if you have suggestions or scripts to add to this public repo. 

Licence:
=======
As usual, all code is licensed under the GPL, v3 or later. 
