from dave import Dave
import time
import random
from datetime import datetime
import traceback

BASEURL = '/home/maximilian/Documents/sudo/davidsniff/'
# BASEURL = '/Users/maximilianweber/Documents/sudo/davesniff/'
ERRORLOG = BASEURL + 'errorlog.txt'
sniff = Dave()
sniff.load_collectors()
