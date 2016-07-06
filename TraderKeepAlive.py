#!/usr/bin/python

#import os
import subprocess
from time import sleep

#while(1):
#
#    PIDFile = open("TraderPID.pid", "r")
#    PID = PIDFile.readln()
#    PIDFile.close()
#
#    if os.path.exists("/proc/" + str(PID)) is False:
#        ## Spawn a new process ##
#
#
#    sleep(300) ## Sleep for 5 Minutes

Exit = False
while(Exit is False):

    #Run the Trader. If it fails. Re-run.

    try:
        a =  subprocess.call(["python", "Trader.py"])
    except KeyboardInterrupt:
        Exit = True
    except Exception:
        print("Crashed, - Re-running")

    sleep(300)
