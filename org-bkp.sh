#!/usr/bin/env bash
########################################################################
# Script Name          : ORG-BKP.sh
# Author               : Lal Pasha Shaik
# Creation Date        : 29-Jun-2016
# Description          : Install and configure incrbkp.py tool
#                        incrbkp.py is python program to take backups 
########################################################################

# Trap on Error
set -e

## Variables
########################################################################
# sourced from /etc/org-install/config
# listed in the configvars variable on next line
configvars="pkgurl"

# Source the /etc/org-install/config file
# Exit if the /etc/org-install/config file is not found
if [ ! -f /etc/org-install/config ]; then
echo "ERROR: /etc/org-install/config file not found."
  exit 1
else
source /etc/org-install/config
fi

for configvar in ${configvars}
do
  if [[ -z $(eval "echo \$$configvar") ]]; then
echo "ERROR: ${configvar} not defined in /etc/org-install/config."
    exit 1
  fi
done

## Logging
#####################################################################
logdir=${logdir:-/var/adm/install-logs}
[[ -d $logdir ]] || mkdir -p $logdir
logfile=$logdir/${0##*/}.$(date +%Y%m%d-%H%M%S).log
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec 1>${logfile} 2>&1

tempdir=$(mktemp -d /tmp/orgtmp.XXXXXXXXXX)
cd ${tempdir}

#syslog
logger -s -- "[$$] $0 start: $(date)"
logger -s -- "[$$] script started in $(pwd)"
logger -s -- "[$$] logfile is in $logfile"

export PS4="+ [\t] "

## Functions
#####################################################################

function cleanup_before_exit() {
  logger -s -- "[$$] $0 end :  $(date)"
  echo "$0 end: $(date)" >&3
  if [[ "${err}" != "0" ]] ; then
    cat ${logfile} >&3
  fi
  cd /tmp && rm -rf ${tempdir}
}

## Main
#####################################################################
trap cleanup_before_exit EXIT
echo "$0 start: $(date)" >&3

#Download the incrbkp.py file
pkgserver=$(grep '^pkgurl' /etc/org-install/config | cut -d/ -f3)
url=http://${pkgserver}/install/scripts

if curl --output /dev/null --silent --head --fail ${url}/incrbkp.py ; then
    curl -k ${url}/incrbkp.py -o /usr/bin/incrbkp
  else
    echo "ERROR: (Line#${LINENUM}) Unable to download incrbkp.py from ${url}"
fi

if [[ -f /usr/bin/incrbkp ]] ; then
	chmod 755 /usr/bin/incrbkp  
else 
	echo "incrbkp file not found"
	exit 1
fi 

# install rsync
if ! rpm -q --quiet rsync ; then
	yum -y install rsync
fi

# Create the Backup configuration file (format: JSON) 
# This file will be used by the incrbkp tool.
# To decide which dirs to backup and which file types to ignore. 

# We are backing only /home directory.
cat > /etc/bkp.conf <<-EOFa
{
  "backup" : [
    "/home"
  ],
  "exclude" : [
    "*.iso"
  ]
}
EOFa

# incrbkp need ssh password less setup.
# generate ssh-keys and upload to backup server.
# backup server admin has to copy that key to authorized_keys
echo -e "\n" | ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa
curl -i -F name=pub -F "uploadedfile=@/root/.ssh/id_rsa.pub" http://10.1.1.2/rsa/upload.php

# Create a cronjob to run the weekly backups.
echo '0 0 * * 7 /usr/bin/incrbkp -n weekly -s 10.1.1.2 -c /etc/bkp.conf -t /client_backups > /var/adm/bkp.log 2>/dev/null' > /etc/cron.d/weeklybkp

# set err
err=0