#!/usr/bin/python
########################################################################
# Script Name          : incrbkp.py
# Author               : LAL PASHA SHAIK 
# Creation Date        : 29-Jun-2016
# Description          : An incremental backup system that uses rsync 
#                        To take backups.
# Copyright (c) 2016 UCM
########################################################################
import sys
import string
import shutil
import getopt
import os
import os.path
import syslog
import errno
import logging
import tempfile
import datetime
import subprocess
import json

from operator import itemgetter
from sys import argv


"""
Takes the incremental Backup. 
Using Rsync.
"""

class IncrementalBackup:
    
    def __init__(self, name="backup", server=None, keep=90, store=None,config_file=None, user="root"):
        self.name = name
        self.server = server
        self.keep = keep
        self.config_file = config_file
        self.store = store 
        self.user = user
        
    def run_command(self,command=None,shell=False,ignore_errors=False,ignore_codes=None):
        result = subprocess.call(command,shell=False)
        if result and not ignore_errors and not ignore_codes:
            raise BaseException(str(command) + " " + str(result))
    
    def backup(self):
        
        rsync_to = None
        now = datetime.datetime.now()
        padding = len(str(self.keep))
        tstamp = now.strftime("%Y%m%d%H%M%S")
        uname = os.uname()[1]
        zbackup_name = string.join(["".zfill(padding),uname, tstamp, self.name], ".")

        rsync_to = self.store + os.sep + zbackup_name
        
        rsync_base = ["rsync", "-avR", "--ignore-errors", "--delete", "--delete-excluded"]
        
        # get the paths to backup 
        bpaths = []
        expaths = []
        
        if self.config_file:
            
            pf = open(self.config_file, "r")
            config = json.load(pf)
            pf.close()
            
            # add the paths 
            bpaths.extend(config["backup"])
            
            # add and filter exclude options 
            if "exclude" in config:
                for exclude in config["exclude"]:
                    rsync_base.extend(["--exclude", exclude])
        
        # one rsync command per path
        for bpath in bpaths:
            bpath = bpath.strip()
            rsync_cmd = rsync_base[:]
            if self.server:
                bkpmaster = self.user + "@" + self.server + ":" + rsync_to
            rsync_cmd.append(bpath)
            rsync_cmd.append(bkpmaster)
            logging.debug(rsync_cmd)
            self.run_command(command=rsync_cmd,ignore_errors=True)
            
def usage():
    usage = ["incrbkp.py [-hnksctu]\n"]
    usage.append("  [-h | --help] prints this help and usage message\n")
    usage.append("  [-n | --name] backup namespace\n")
    usage.append("  [-k | --keep] number of backups to keep before deleting\n")
    usage.append("  [-s | --server] the server to keep the backup, (eg:10.1.1.2)\n")
    usage.append("  [-c | --config] configuration file with backup paths\n")
    usage.append("  [-t | --store] directory to store the backups in backup master\n")
    usage.append("  [-u | --user] the remote username used to ssh for backups\n")
    message = string.join(usage)
    print message
         
"""
Main method
"""
    
def main(argv):
        
    pid_file = tempfile.gettempdir() + os.sep + "incrbkp.pid"
    name = "backup"
    keep = 90
    server = None
    config_file = None
    store = None
    user = "backup"
    
    try:
        opts,args = getopt.getopt(argv, "hn:k:s:c:t:u:", ["help","name=","keep=","server=","config=","store=","user="])
            
        if len(argv) == 0:
            usage()
            sys.exit()
                
        for opt,arg in opts:
            if opt in ("-h", "--help"):
                usage()
                sys.exit()
            elif opt in ("-n", "--name"):                
                name = arg
            elif opt in ("-k", "--keep"):                
                keep = int(arg)
            elif opt in ("-s", "--server"):                
                server = arg                
            elif opt in ("-c", "--config"): 
                config_file = arg
            elif opt in ("-t", "--store"): 
                store = arg
            elif opt in ("-u", "--user"): 
                user = arg
                    
    except getopt.GetoptError, msg:
        usage()
        sys.exit(errno.EIO)
                
         # check options are set correctly
    if config_file == None or store == None:
        usage()                          
        sys.exit(errno.EPERM)
             
    try:
            
        if os.path.exists(pid_file):
            logging.warning("Backup running, %s pid exists, exiting" % pid_file)
            sys.exit(errno.EBUSY)
        else:
            pid = str(os.getpid())
            f = open(pid_file, "w")
            f.write("%s\n" % pid)
            f.close()
            
        # Create the object and pass the details  
        ibkp = IncrementalBackup(name, server, keep, store, config_file, user)
        ibkp.backup()
        
    except(Exception):
        logging.exception("Incremental Backup Failed")
    finally:
        os.remove(pid_file)
        
        
if __name__ == "__main__":
    main(sys.argv[1:])
    
    
    
                
          
                    
         
        
