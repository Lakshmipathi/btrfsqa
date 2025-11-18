# BTRFSQA Architecture Diagrams

This document contains detailed architecture diagrams for the BTRFSQA system.

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow Diagram](#data-flow-diagram)
4. [Execution Sequence](#execution-sequence)
5. [Infrastructure Layout](#infrastructure-layout)
6. [Network Topology](#network-topology)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BTRFSQA SYSTEM                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
        ┌───────────────┐   ┌───────────────┐  ┌──────────────┐
        │ Control Plane │   │ Test Platform │  │  Publishing  │
        │   (Local)     │   │   (AWS EC2)   │  │   (GitHub)   │
        └───────────────┘   └───────────────┘  └──────────────┘
                │                   │                   │
                │                   │                   │
        ┌───────▼─────────┐ ┌───────▼────────┐ ┌──────▼───────┐
        │  btrfsqa.py     │ │ BTRFS Kernel   │ │ GitHub Pages │
        │  Orchestrator   │ │ Test Suites    │ │  Dashboard   │
        │  • Provision    │ │ • btrfsprogs   │ │ • Results    │
        │  • Configure    │ │ • xfstests     │ │ • Recordings │
        │  • Execute      │ │ • RAID tests   │ │ • Logs       │
        │  • Collect      │ │                │ │              │
        │  • Publish      │ │                │ │              │
        └─────────────────┘ └────────────────┘ └──────────────┘
```

---

## Component Architecture

### Detailed Component Breakdown

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE (Local Machine)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      btrfsqa.py Orchestrator                        │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                     │ │
│  │  ┌───────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │ │
│  │  │  AWS Manager      │  │  Config Manager  │  │ Remote Executor │ │ │
│  │  ├───────────────────┤  ├──────────────────┤  ├─────────────────┤ │ │
│  │  │ • Boto Client     │  │ • JSON Parser    │  │ • Fabric SSH    │ │ │
│  │  │ • EC2 Operations  │  │ • File Loader    │  │ • File Upload   │ │ │
│  │  │   - RunInstances  │  │ • Validation     │  │ • Sudo Commands │ │ │
│  │  │   - Terminate     │  │                  │  │ • Reboot Handle │ │ │
│  │  │   - CreateTags    │  │ Configs:         │  │                 │ │ │
│  │  │   - DeleteVolume  │  │ • aws_auth.json  │  │ Functions:      │ │ │
│  │  │ • Spot Requests   │  │ • ec2.json       │  │ • run()         │ │ │
│  │  │ • Volume Mgmt     │  │ • github.json    │  │ • put()         │ │ │
│  │  │                   │  │ • timeout.json   │  │ • sudo()        │ │ │
│  │  └───────────────────┘  └──────────────────┘  └─────────────────┘ │ │
│  │                                                                     │ │
│  │  ┌───────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │ │
│  │  │ Results Publisher │  │  Log Collector   │  │ Status Tracker  │ │ │
│  │  ├───────────────────┤  ├──────────────────┤  ├─────────────────┤ │ │
│  │  │ • Git Clone       │  │ • Download Logs  │  │ • Completion    │ │ │
│  │  │ • HTML Generator  │  │ • Asciinema URLs │  │   Detection     │ │ │
│  │  │ • Table Builder   │  │ • Result Parsing │  │ • Timeout       │ │ │
│  │  │ • Git Commit      │  │ • File Transfer  │  │   Management    │ │ │
│  │  │ • Git Push        │  │                  │  │ • Pass/Fail     │ │ │
│  │  │                   │  │                  │  │   Determination │ │ │
│  │  └───────────────────┘  └──────────────────┘  └─────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  Configuration Files:                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ aws_auth.json│ │  ec2.json    │ │ github.json  │ │timeout.json  │  │
│  │              │ │              │ │              │ │              │  │
│  │ • AccessKey  │ │ • AMI ID     │ │ • Repo URL   │ │ • 001: 120   │  │
│  │ • SecretKey  │ │ • Type       │ │ • Username   │ │ • 002: 120   │  │
│  │ • Region     │ │ • KeyPair    │ │ • Password   │ │ • 003: 120   │  │
│  │              │ │ • SecGroup   │ │              │ │ • 004: 30    │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    TEST ENVIRONMENT (AWS EC2 Instance)                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Instance: r4.large │ OS: Fedora 26 │ Type: Spot │ Region: us-east-1   │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    LAYER 1: Operating System                        │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  Fedora 26 (Base Installation)                                     │ │
│  │  • systemd                                                          │ │
│  │  • grub2 bootloader                                                 │ │
│  │  • dnf package manager                                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  │                                       │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              LAYER 2: BTRFS Development Kernel                      │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  Linux Kernel 4.14.0-rc6+ (btrfs-devel/misc-next)                  │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │ BTRFS Kernel Module (CONFIG_BTRFS_FS=m)                      │  │ │
│  │  │ • CONFIG_BTRFS_FS_POSIX_ACL=y                                │  │ │
│  │  │ • CONFIG_BTRFS_FS_CHECK_INTEGRITY=y                          │  │ │
│  │  │ • CONFIG_BTRFS_FS_RUN_SANITY_TESTS=y                         │  │ │
│  │  │ • CONFIG_BTRFS_DEBUG=y                                       │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  │                                       │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              LAYER 3: Test Execution Framework                      │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │ Asciinema Recording Layer                                    │  │ │
│  │  │  asciinema rec -c "bash SCRIPT.sh" /tmp/SCRIPT.json         │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  │                                  │                                  │ │
│  │                                  ▼                                  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │ │
│  │  │ Script 001   │  │ Script 002   │  │ Script 003   │             │ │
│  │  │              │  │              │  │              │             │ │
│  │  │ Kernel Build │  │ btrfsprogs   │  │ xfstests     │             │ │
│  │  │              │  │  Tests       │  │  Suite       │             │ │
│  │  │ • Clone      │  │              │  │              │             │ │
│  │  │ • Configure  │  │ • fsck       │  │ • generic/   │             │ │
│  │  │ • Compile    │  │ • cli        │  │ • btrfs/     │             │ │
│  │  │ • Install    │  │ • misc       │  │ • shared/    │             │ │
│  │  │ • Reboot     │  │ • fuzz       │  │              │             │ │
│  │  │              │  │              │  │ 400+ tests   │             │ │
│  │  │ Timeout: 120m│  │ Timeout: 120m│  │ Timeout: 120m│             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  │                                                                     │ │
│  │  ┌──────────────┐                                                  │ │
│  │  │ Script 004   │                                                  │ │
│  │  │              │                                                  │ │
│  │  │ RAID5 Scrub  │                                                  │ │
│  │  │              │                                                  │ │
│  │  │ • Patch      │                                                  │ │
│  │  │ • RAID5 Ops  │                                                  │ │
│  │  │ • Scrub      │                                                  │ │
│  │  │              │                                                  │ │
│  │  │ Timeout: 30m │                                                  │ │
│  │  └──────────────┘                                                  │ │
│  │                                                                     │ │
│  │  Completion Protocol:                                              │ │
│  │  touch /tmp/SCRIPTNAME.completed  ← Signals success               │ │
│  │                                                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  │                                       │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              LAYER 4: Storage Infrastructure                        │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                     │ │
│  │  Root Volume:  /dev/xvda  (8-10 GB, OS & packages)                │ │
│  │                                                                     │ │
│  │  Test Volumes:                                                     │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ /dev/xvdb  (20 GB, GP2)  ← TEST_DEV (primary test device)   │ │ │
│  │  ├──────────────────────────────────────────────────────────────┤ │ │
│  │  │ /dev/xvdc  (20 GB, GP2)  ┐                                   │ │ │
│  │  │ /dev/xvdd  (20 GB, GP2)  │                                   │ │ │
│  │  │ /dev/xvde  (20 GB, GP2)  ├─ SCRATCH_DEV_POOL (multi-disk)   │ │ │
│  │  │ /dev/xvdf  (20 GB, GP2)  │                                   │ │ │
│  │  │ /dev/xvdg  (20 GB, GP2)  ┘                                   │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  │                                                                     │ │
│  │  Mount Points:                                                     │ │
│  │  • /mnt/test    (TEST_DIR)                                        │ │
│  │  • /mnt/scratch (SCRATCH_MNT)                                     │ │
│  │                                                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         PUBLISHING LAYER                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Asciinema.org                                  │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  • Terminal recording hosting                                      │ │
│  │  • Public URLs: https://asciinema.org/a/RECORDING_ID              │ │
│  │  • Embeddable JavaScript players                                  │ │
│  │  • Thumbnail previews                                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    GitHub Repository                                │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │                                                                     │ │
│  │  Repository: Lakshmipathi/btrfsqa                                  │ │
│  │                                                                     │ │
│  │  Structure:                                                        │ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │ │
│  │  │ _layouts/default.html          ← Dynamically updated          │ │ │
│  │  │   • Header (project info)                                     │ │ │
│  │  │   • Results table (latest test runs)                          │ │ │
│  │  │   • Footer (known issues)                                     │ │ │
│  │  ├───────────────────────────────────────────────────────────────┤ │ │
│  │  │ results/                       ← Test outputs                 │ │ │
│  │  │   └─ results_YYYY-MM-DD_HH:MM/                                │ │ │
│  │  │      ├─ btrfsprogs_*/                                         │ │ │
│  │  │      ├─ xfstests_*/                                           │ │ │
│  │  │      └─ logs/                                                 │ │ │
│  │  │         ├─ 001_btrfsdevel.log                                 │ │ │
│  │  │         ├─ 002_btrfsprogs.log                                 │ │ │
│  │  │         ├─ 003_xfstests.log                                   │ │ │
│  │  │         └─ 004_raid5_scrub.log                                │ │ │
│  │  ├───────────────────────────────────────────────────────────────┤ │ │
│  │  │ _config.yml                    ← Jekyll configuration         │ │ │
│  │  │   theme: jekyll-theme-cayman                                  │ │ │
│  │  │   title: BTRFSQA Dashboard                                    │ │ │
│  │  └───────────────────────────────────────────────────────────────┘ │ │
│  │                                                                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                  │                                       │
│                                  │ Triggers build                        │
│                                  ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     GitHub Pages                                    │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  • Jekyll static site generator                                    │ │
│  │  • Automatic deployment on push                                    │ │
│  │  • HTTPS enabled                                                   │ │
│  │  • CDN distribution                                                │ │
│  │                                                                     │ │
│  │  Public URL: https://lakshmipathi.github.io/btrfsqa               │ │
│  │                                                                     │ │
│  │  Content:                                                          │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ Results Table (HTML)                                          │ │ │
│  │  │ ┌────────┬────────┬───────────────┬──────────────┐           │ │ │
│  │  │ │ Script │ Status │ Screencast    │ Logs         │           │ │ │
│  │  │ ├────────┼────────┼───────────────┼──────────────┤           │ │ │
│  │  │ │ 001    │  PASS  │ [▶ Player]    │ [Download]   │           │ │ │
│  │  │ │ 002    │  PASS  │ [▶ Player]    │ [Download]   │           │ │ │
│  │  │ │ 003    │  FAIL  │ [▶ Player]    │ [Download]   │           │ │ │
│  │  │ │ 004    │  PASS  │ [▶ Player]    │ [Download]   │           │ │ │
│  │  │ └────────┴────────┴───────────────┴──────────────┘           │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BTRFSQA DATA FLOW                                │
└─────────────────────────────────────────────────────────────────────────┘

START
  │
  │ [1] Read Configuration
  ├──────────────────────────────────────────────┐
  │                                               │
  ▼                                               ▼
┌──────────────────┐                      ┌──────────────────┐
│ Local Filesystem │                      │ Config Files     │
│                  │                      │                  │
│ setup/config/    │─────────────────────▶│ • aws_auth.json  │
│                  │   Load & Parse       │ • ec2.json       │
│                  │                      │ • github.json    │
│                  │                      │ • timeout.json   │
└──────────────────┘                      └──────────────────┘
                                                  │
                                                  │
  ┌───────────────────────────────────────────────┘
  │
  │ [2] Provision Infrastructure
  ▼
┌──────────────────────────────────────────────────────────────┐
│                         AWS API                               │
│                                                               │
│  btrfsqa.py ─────request_spot_instance()──────▶ EC2 Service │
│      │                                                │       │
│      │                                                ▼       │
│      │                                          Create:       │
│      │                                          • Instance    │
│      │                                          • 6x Volumes  │
│      │                                          • Tags        │
│      │                                                │       │
│      │◀────────────instance_details───────────────────┘       │
│      │           (IP, instance_id, volume_ids)                │
└──────┼───────────────────────────────────────────────────────┘
       │
       │ [3] Upload Configuration & Scripts
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    SSH/Fabric Transfer                        │
│                                                               │
│  Local                           EC2 Instance                │
│  ─────────────────────────────────────────────────────────── │
│                                                               │
│  setup/config/kernel.config ────▶ /tmp/kernel.config        │
│  setup/config/local.config  ────▶ /tmp/local.config         │
│  setup/config/bashrc        ────▶ /tmp/bashrc               │
│  setup/config/netrc         ────▶ /root/.netrc              │
│  setup/scripts/001_*        ────▶ /root/001_btrfsdevel      │
│  setup/scripts/002_*        ────▶ /root/002_btrfsprogs      │
│  setup/scripts/003_*        ────▶ /root/003_xfstests        │
│  setup/scripts/004_*        ────▶ /root/004_raid5_scrub     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
       │
       │ [4] Execute Tests
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Test Execution (EC2)                       │
│                                                               │
│  For each script in [001, 002, 003, 004]:                   │
│                                                               │
│    Start Recording                                           │
│      │                                                        │
│      ▼                                                        │
│    ┌─────────────────────────────────────────────────┐      │
│    │ asciinema rec -c "bash SCRIPT" /tmp/SCRIPT.json│       │
│    └─────────────────────────────────────────────────┘      │
│      │                                                        │
│      ▼                                                        │
│    Execute Script                                            │
│      │                                                        │
│      ├──▶ Download source code (git clone)                  │
│      ├──▶ Build/compile                                     │
│      ├──▶ Run tests                                         │
│      ├──▶ Capture output to /tmp/SCRIPT.log                │
│      │                                                        │
│      ▼                                                        │
│    Success?                                                  │
│      │                                                        │
│      ├─YES─▶ touch /tmp/SCRIPT.completed                    │
│      └─NO──▶ (no completion marker)                         │
│                                                               │
│    Stop Recording                                            │
│      │                                                        │
│      ▼                                                        │
│    Upload Recording                                          │
│      │                                                        │
│      ▼                                                        │
│    ┌─────────────────────────────────────────────────┐      │
│    │ asciinema upload /tmp/SCRIPT.json               │      │
│    │           ↓                                      │      │
│    │   Returns: https://asciinema.org/a/XXXXXX      │      │
│    └─────────────────────────────────────────────────┘      │
│      │                                                        │
│      └──▶ Save URL to /tmp/SCRIPT.url                       │
│                                                               │
└───────────────────────────────────────────────────────────────┘
       │
       │ [5] Collect Results
       ▼
┌──────────────────────────────────────────────────────────────┐
│                  Results Collection (SSH)                     │
│                                                               │
│  EC2 ──────────────────────────────────────────▶ Local      │
│                                                               │
│  For each script:                                            │
│    /tmp/SCRIPT.log          ────▶  results/logs/SCRIPT.log  │
│    /tmp/SCRIPT.url          ────▶  (parse for HTML)         │
│    /tmp/SCRIPT.completed    ────▶  (check existence)        │
│                                                               │
│  Status Determination:                                       │
│    IF completion file exists:                                │
│      status = "PASS"                                         │
│    ELSE:                                                     │
│      status = "FAIL"                                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
       │
       │ [6] Generate Results Page
       ▼
┌──────────────────────────────────────────────────────────────┐
│                  HTML Generation (Local)                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ update_htmltable()                                      │ │
│  │                                                         │ │
│  │ For each test result:                                  │ │
│  │   Generate HTML table row:                             │ │
│  │   ┌─────────────────────────────────────────────────┐ │ │
│  │   │ <tr>                                             │ │ │
│  │   │   <td>Script Name</td>                           │ │ │
│  │   │   <td><span class="status-PASS|FAIL">...</span> │ │ │
│  │   │   <td><script src="asciinema_url.js"></script>  │ │ │
│  │   │   <td><a href="log_file">Download</a></td>      │ │ │
│  │   │ </tr>                                            │ │ │
│  │   └─────────────────────────────────────────────────┘ │ │
│  │                                                         │ │
│  │ Insert rows into _layouts/default.html                 │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
       │
       │ [7] Publish to GitHub
       ▼
┌──────────────────────────────────────────────────────────────┐
│                   Git Operations (Local)                      │
│                                                               │
│  git clone https://github.com/USER/btrfsqa.git /tmp/repo    │
│  cd /tmp/repo                                                │
│  cp -r results/* results/                                    │
│  cp _layouts/default.html _layouts/default.html             │
│  git add .                                                   │
│  git commit -m "Update results - YYYY-MM-DD HH:MM"          │
│  git push origin master                                     │
│           │                                                   │
│           └──────────────────────────────────────┐           │
└──────────────────────────────────────────────────┼───────────┘
                                                    │
                                                    │ Push event
                                                    ▼
┌──────────────────────────────────────────────────────────────┐
│                     GitHub Backend                            │
│                                                               │
│  Receive push ──▶ Trigger GitHub Pages build                │
│                         │                                     │
│                         ▼                                     │
│                   Jekyll Build                               │
│                   • Process markdown                         │
│                   • Apply theme                              │
│                   • Generate static HTML                     │
│                         │                                     │
│                         ▼                                     │
│                   Deploy to CDN                              │
│                         │                                     │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          │ Accessible at
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              Public Dashboard (GitHub Pages)                  │
│                                                               │
│  https://lakshmipathi.github.io/btrfsqa                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ BTRFSQA Test Results                                    │ │
│  │                                                         │ │
│  │ Latest Run: 2024-11-18 10:30                           │ │
│  │                                                         │ │
│  │ ┌──────┬────────┬─────────────┬───────────┐           │ │
│  │ │Script│ Status │ Screencast  │ Logs      │           │ │
│  │ ├──────┼────────┼─────────────┼───────────┤           │ │
│  │ │ 001  │  ✓     │ [▶ Play]    │ [↓ Log]   │           │ │
│  │ │ 002  │  ✓     │ [▶ Play]    │ [↓ Log]   │           │ │
│  │ │ 003  │  ✗     │ [▶ Play]    │ [↓ Log]   │           │ │
│  │ │ 004  │  ✓     │ [▶ Play]    │ [↓ Log]   │           │ │
│  │ └──────┴────────┴─────────────┴───────────┘           │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘

END
```

---

## Execution Sequence

### Detailed Sequence Diagram

```
┌──────────┐         ┌──────┐         ┌─────────┐       ┌────────┐      ┌─────────┐
│btrfsqa.py│         │ AWS  │         │EC2 Inst │       │ GitHub │      │ GH Pages│
└────┬─────┘         └──┬───┘         └────┬────┘       └───┬────┘      └────┬────┘
     │                  │                   │                │                │
     │ [INITIALIZATION] │                   │                │                │
     ├──Load configs────▶                   │                │                │
     │◀─Config data─────┤                   │                │                │
     │                  │                   │                │                │
     │ [PROVISIONING]   │                   │                │                │
     ├──Request spot────▶                   │                │                │
     │  instance        │                   │                │                │
     │                  ├───Launch──────────▶                │                │
     │                  │   r4.large        │                │                │
     │                  │   + 6 EBS         │                │                │
     │                  │                   │                │                │
     │◀─Instance ready──┤                   │                │                │
     │  (IP address)    │                   │                │                │
     │                  │                   │                │                │
     │ [SETUP]          │                   │                │                │
     ├──SSH connect─────┼───────────────────▶                │                │
     │                  │                   │                │                │
     ├──Upload configs──┼───────────────────▶                │                │
     │  (kernel.config, │                   │                │                │
     │   local.config)  │                   │                │                │
     │                  │                   │                │                │
     ├──Upload scripts──┼───────────────────▶                │                │
     │  (001-004)       │                   │                │                │
     │                  │                   │                │                │
     ├──Install deps────┼───────────────────▶                │                │
     │  (git, asciinema)│                   │                │                │
     │                  │                   │                │                │
     │ [SCRIPT 001]     │                   │                │                │
     ├──Execute 001─────┼───────────────────▶                │                │
     │  (kernel build)  │                   │                │                │
     │                  │                   ├──git clone─────▶ (btrfs-devel) │
     │                  │                   │  kernel source │                │
     │                  │                   ├──Compile───────┤                │
     │                  │                   │  (120 min)     │                │
     │                  │                   ├──Install───────┤                │
     │                  │                   ├──Reboot────────┤                │
     │                  │         [RECONNECT]                │                │
     │◀─Wait SSH────────┼───────────────────┤                │                │
     │                  │                   │                │                │
     │                  │                   ├──Upload────────▶ (asciinema.org)│
     │                  │                   │  recording     │                │
     │◀─Script complete─┼───────────────────┤                │                │
     │  (001.completed) │                   │                │                │
     │                  │                   │                │                │
     │ [SCRIPT 002]     │                   │                │                │
     ├──Execute 002─────┼───────────────────▶                │                │
     │  (btrfsprogs)    │                   │                │                │
     │                  │                   ├──git clone─────▶ (btrfsprogs)  │
     │                  │                   ├──Build & test──┤                │
     │                  │                   │  (120 min)     │                │
     │                  │                   ├──Upload rec────▶ (asciinema.org)│
     │◀─Script complete─┼───────────────────┤                │                │
     │                  │                   │                │                │
     │ [SCRIPT 003]     │                   │                │                │
     ├──Execute 003─────┼───────────────────▶                │                │
     │  (xfstests)      │                   │                │                │
     │                  │                   ├──git clone─────▶ (xfstests)    │
     │                  │                   ├──Run tests─────┤                │
     │                  │                   │  (120 min)     │                │
     │                  │                   ├──Upload rec────▶ (asciinema.org)│
     │◀─Script complete─┼───────────────────┤                │                │
     │                  │                   │                │                │
     │ [SCRIPT 004]     │                   │                │                │
     ├──Execute 004─────┼───────────────────▶                │                │
     │  (raid5 scrub)   │                   │                │                │
     │                  │                   ├──Patch & test──┤                │
     │                  │                   │  (30 min)      │                │
     │                  │                   ├──Upload rec────▶ (asciinema.org)│
     │◀─Script complete─┼───────────────────┤                │                │
     │                  │                   │                │                │
     │ [RESULTS]        │                   │                │                │
     ├──Download logs───┼───────────────────▶                │                │
     │◀─Log files───────┼───────────────────┤                │                │
     │                  │                   │                │                │
     ├──Generate HTML───┤                   │                │                │
     │  (results table) │                   │                │                │
     │                  │                   │                │                │
     ├──git clone───────┼───────────────────┼────────────────▶                │
     │◀─Repository──────┼───────────────────┼────────────────┤                │
     │                  │                   │                │                │
     ├──Copy results────┤                   │                │                │
     │  & HTML          │                   │                │                │
     │                  │                   │                │                │
     ├──git commit──────┤                   │                │                │
     ├──git push────────┼───────────────────┼────────────────▶                │
     │                  │                   │                ├──Trigger───────▶
     │                  │                   │                │  Jekyll build  │
     │                  │                   │                │                │
     │                  │                   │                │◀─Deploy────────┤
     │                  │                   │                │  website       │
     │                  │                   │                │                │
     │ [CLEANUP]        │                   │                │                │
     ├──Wait 2 min──────┤                   │                │                │
     │                  │                   │                │                │
     ├──Terminate inst──▶                   │                │                │
     │                  ├───Terminate───────▶                │                │
     │                  │                   │                │                │
     ├──Delete volumes──▶                   │                │                │
     │                  ├───Delete EBS──────┤                │                │
     │                  │                   │                │                │
     │◀─Cleanup done────┤                   │                │                │
     │                  │                   │                │                │
    END                 │                   │                │                │
```

---

## Infrastructure Layout

### AWS Resource Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AWS Region: us-east-1                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         VPC (Default)                               │ │
│  │                                                                     │ │
│  │  ┌────────────────────────────────────────────────────────────────┐││
│  │  │                  Public Subnet                                  │││
│  │  │                                                                 │││
│  │  │  ┌──────────────────────────────────────────────────────────┐ │││
│  │  │  │  EC2 Instance: btrfsqa-2024-11-18                        │ │││
│  │  │  │                                                           │ │││
│  │  │  │  Type: r4.large                                          │ │││
│  │  │  │  • 2 vCPUs (Intel Xeon E5-2686 v4)                       │ │││
│  │  │  │  • 15.25 GB RAM                                           │ │││
│  │  │  │  • Up to 10 Gbps network                                 │ │││
│  │  │  │  • EBS-optimized                                          │ │││
│  │  │  │                                                           │ │││
│  │  │  │  AMI: Fedora 26 (ami-xxxxxxxx)                           │ │││
│  │  │  │  Purchase: Spot Instance                                 │ │││
│  │  │  │  KeyPair: btrfsqa-keypair                                │ │││
│  │  │  │                                                           │ │││
│  │  │  │  ┌─────────────────────────────────────────────────────┐ │ │││
│  │  │  │  │ Network Interfaces                                   │ │ │││
│  │  │  │  │                                                       │ │ │││
│  │  │  │  │ eth0:                                                │ │ │││
│  │  │  │  │  • Public IP: 54.xxx.xxx.xxx (dynamic)              │ │ │││
│  │  │  │  │  • Private IP: 172.31.x.x                           │ │ │││
│  │  │  │  │  • Security Group: btrfsqa-sg                       │ │ │││
│  │  │  │  │    - Inbound: TCP 22 (SSH) from 0.0.0.0/0          │ │ │││
│  │  │  │  │    - Outbound: All traffic                          │ │ │││
│  │  │  │  └─────────────────────────────────────────────────────┘ │ │││
│  │  │  │                                                           │ │││
│  │  │  │  ┌─────────────────────────────────────────────────────┐ │ │││
│  │  │  │  │ Block Devices                                        │ │ │││
│  │  │  │  │                                                       │ │ │││
│  │  │  │  │ /dev/xvda:  Root (8-10 GB, GP2)                     │ │ │││
│  │  │  │  │             Delete on termination: Yes               │ │ │││
│  │  │  │  │             ┌──────────────────────────────────────┐ │ │ │││
│  │  │  │  │             │ Fedora 26 OS                         │ │ │ │││
│  │  │  │  │             │ • /boot (kernel)                     │ │ │ │││
│  │  │  │  │             │ • / (rootfs)                         │ │ │ │││
│  │  │  │  │             │ • /tmp (test scripts & logs)         │ │ │ │││
│  │  │  │  │             └──────────────────────────────────────┘ │ │ │││
│  │  │  │  │                                                       │ │ │││
│  │  │  │  │ /dev/xvdb:  Test Device (20 GB, GP2)                │ │ │││
│  │  │  │  │             Delete on termination: Yes               │ │ │││
│  │  │  │  │             Used as: TEST_DEV                        │ │ │││
│  │  │  │  │                                                       │ │ │││
│  │  │  │  │ /dev/xvdc:  Scratch 1 (20 GB, GP2)                  │ │ │││
│  │  │  │  │ /dev/xvdd:  Scratch 2 (20 GB, GP2)                  │ │ │││
│  │  │  │  │ /dev/xvde:  Scratch 3 (20 GB, GP2)                  │ │ │││
│  │  │  │  │ /dev/xvdf:  Scratch 4 (20 GB, GP2)                  │ │ │││
│  │  │  │  │ /dev/xvdg:  Scratch 5 (20 GB, GP2)                  │ │ │││
│  │  │  │  │             Delete on termination: Yes               │ │ │││
│  │  │  │  │             Used as: SCRATCH_DEV_POOL                │ │ │││
│  │  │  │  │                                                       │ │ │││
│  │  │  │  │ Total Storage: 128 GB (8+120 GB)                    │ │ │││
│  │  │  │  │ Volume Type: GP2 (General Purpose SSD)              │ │ │││
│  │  │  │  │ IOPS: 100 per volume (baseline)                     │ │ │││
│  │  │  │  └─────────────────────────────────────────────────────┘ │ │││
│  │  │  │                                                           │ │││
│  │  │  │  Tags:                                                   │ │││
│  │  │  │  • Name: btrfsqa-2024-11-18                             │ │││
│  │  │  │  • Project: btrfsqa                                     │ │││
│  │  │  │  • ManagedBy: automation                                │ │││
│  │  │  │                                                           │ │││
│  │  │  │  Lifecycle:                                              │ │││
│  │  │  │  • Launch: On-demand via Boto                           │ │││
│  │  │  │  • Duration: 4-6 hours (typical)                        │ │││
│  │  │  │  • Termination: Automatic after results published       │ │││
│  │  │  └──────────────────────────────────────────────────────────┘ │││
│  │  │                                                                 │││
│  │  │  Internet Gateway                                              │││
│  │  │  ┌─────────────────────────────────────────────────────────┐  │││
│  │  │  │ Routes:                                                  │  │││
│  │  │  │ • 0.0.0.0/0 → Internet Gateway (outbound)               │  │││
│  │  │  └─────────────────────────────────────────────────────────┘  │││
│  │  └────────────────────────────────────────────────────────────────┘││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Cost Estimate (per run, ~4 hours):                                    │
│  • r4.large spot: ~$0.03/hr × 4 = $0.12                                │
│  • EBS GP2: 120 GB × $0.10/GB/mo ÷ 730 hrs × 4 = $0.07                │
│  • Data transfer: Minimal (~$0.01)                                     │
│  • Total: ~$0.20 per test run                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Network Topology

### Communication Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      BTRFSQA NETWORK TOPOLOGY                            │
└─────────────────────────────────────────────────────────────────────────┘


    Internet
       ▲
       │
       │ (HTTPS/SSH)
       │
┌──────┴────────────────────────────────────────────────────────────────┐
│                                                                        │
│  ┌──────────────────────┐                                             │
│  │  Local Control Plane │                                             │
│  │  (Development Machine)                                             │
│  │                      │                                             │
│  │  btrfsqa.py          │                                             │
│  └──────────────────────┘                                             │
│           │                                                            │
│           │                                                            │
│           ├─────[1]─────▶ AWS API (HTTPS:443)                         │
│           │              • EC2:RunInstances                            │
│           │              • EC2:CreateTags                              │
│           │              • EC2:TerminateInstances                      │
│           │              • EC2:DeleteVolume                            │
│           │              Endpoint: ec2.us-east-1.amazonaws.com         │
│           │                                                            │
│           ├─────[2]─────▶ EC2 Public IP (SSH:22)                      │
│           │              • Fabric SSH sessions                         │
│           │              • File transfers (SFTP over SSH)              │
│           │              • Remote command execution                    │
│           │              Protocol: SSH v2                              │
│           │              Auth: btrfsqa-keypair.pem                     │
│           │                                                            │
│           └─────[3]─────▶ GitHub.com (HTTPS:443)                      │
│                          • git clone                                   │
│                          • git push                                    │
│                          Endpoint: github.com                          │
│                          Auth: HTTPS basic (netrc)                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘


┌────────────────────────────────────────────────────────────────────────┐
│                        AWS REGION (us-east-1)                          │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │  EC2 Instance (r4.large)                                          │ │
│  │  Public IP: 54.xxx.xxx.xxx                                        │ │
│  │  Private IP: 172.31.x.x                                           │ │
│  │                                                                   │ │
│  │  Security Group: btrfsqa-sg                                       │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ Inbound Rules:                                               │ │ │
│  │  │ • SSH (TCP 22) from 0.0.0.0/0 → Allow                       │ │ │
│  │  │                                                              │ │ │
│  │  │ Outbound Rules:                                              │ │ │
│  │  │ • All traffic to 0.0.0.0/0 → Allow                          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Outbound Connections:                                            │ │
│  │                                                                   │ │
│  │  ├─────[4]─────▶ GitHub.com (HTTPS:443)                          │ │
│  │  │              • git clone (source code)                        │ │
│  │  │              Repositories:                                    │ │
│  │  │              - kdave/btrfs-devel (kernel)                     │ │
│  │  │              - kdave/btrfsprogs (userspace tools)             │ │
│  │  │              - btrfs/xfstests (test suite)                    │ │
│  │  │                                                                │ │
│  │  ├─────[5]─────▶ Fedora Mirrors (HTTP:80, HTTPS:443)            │ │
│  │  │              • dnf package downloads                          │ │
│  │  │              • Kernel dependencies                            │ │
│  │  │              • Build tools (gcc, make, etc.)                  │ │
│  │  │              Mirrors: mirrors.fedoraproject.org               │ │
│  │  │                                                                │ │
│  │  └─────[6]─────▶ Asciinema.org (HTTPS:443)                       │ │
│  │                 • POST /api/asciicasts (upload)                  │ │
│  │                 Returns: Recording URL                           │ │
│  │                 Format: JSON payload                             │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘


┌────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL SERVICES                                │
│                                                                        │
│  ┌──────────────────────┐  ┌──────────────────────────────────────┐  │
│  │    GitHub.com        │  │      Asciinema.org                   │  │
│  │                      │  │                                      │  │
│  │  Receives:           │  │  Receives:                           │  │
│  │  • git push          │  │  • Terminal recordings (JSON)        │  │
│  │  • Results           │  │                                      │  │
│  │  • HTML updates      │  │  Provides:                           │  │
│  │                      │  │  • Public URLs                       │  │
│  │  Triggers:           │  │  • Embeddable players                │  │
│  │  • Jekyll build      │  │  • Thumbnail generation              │  │
│  │  • GitHub Pages      │  │                                      │  │
│  │    deployment        │  │  API Endpoint:                       │  │
│  │                      │  │  POST https://asciinema.org/api/     │  │
│  │  Serves:             │  │       asciicasts                     │  │
│  │  • Public dashboard  │  │                                      │  │
│  │  • Test results      │  │                                      │  │
│  │                      │  │                                      │  │
│  └──────────────────────┘  └──────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘


Data Flows:

[1] Control → AWS API
    Protocol: HTTPS
    Purpose: Provision/terminate infrastructure
    Auth: AWS access key + secret key

[2] Control → EC2 Instance
    Protocol: SSH (port 22)
    Purpose: Configuration, test execution, results collection
    Auth: RSA keypair (btrfsqa-keypair.pem)

[3] Control → GitHub
    Protocol: HTTPS (Git over HTTPS)
    Purpose: Publish results
    Auth: Username + password (via netrc)

[4] EC2 → GitHub
    Protocol: HTTPS
    Purpose: Download source code (kernel, tools, tests)
    Auth: None (public repositories)

[5] EC2 → Fedora Mirrors
    Protocol: HTTP/HTTPS
    Purpose: Package installation
    Auth: None

[6] EC2 → Asciinema.org
    Protocol: HTTPS
    Purpose: Upload terminal recordings
    Auth: None (anonymous uploads)


Network Security Considerations:

✓ SSH uses key-based authentication (no passwords)
✓ AWS credentials stored locally (not in repository)
✓ GitHub credentials in netrc (gitignored)
✗ SSH open to 0.0.0.0/0 (should restrict to known IPs)
✓ All external communication uses HTTPS (encrypted)
✓ Instance terminated after each run (minimal exposure)
✓ Spot instances (cost optimization)
```

---

## Summary

These architecture diagrams provide comprehensive visual documentation of the BTRFSQA system, covering:

1. **System Overview**: High-level component organization
2. **Component Architecture**: Detailed breakdown of all layers and modules
3. **Data Flow**: End-to-end data movement through the system
4. **Execution Sequence**: Step-by-step workflow with timing
5. **Infrastructure Layout**: AWS resource topology and specifications
6. **Network Topology**: Communication paths and security boundaries

This documentation should serve as a reference for understanding, maintaining, and extending the BTRFSQA system.
