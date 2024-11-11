from dave import Dave
from time import sleep
import random
from datetime import datetime, time
import traceback

BASEURL = '/home/pi/davidsniff/'
ERRORLOG = BASEURL + 'errorlog.txt'

print('DAVID SNIFF IS WORKING HERE')
# wait for internet to connect
sleep(20)

def is_time_between(begin_time, end_time):
    # If check time is not given, default to current UTC time
    check_time = datetime.now().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time

def log_to_file(e):
    with open(ERRORLOG, 'a') as f:
        now = datetime.now()
        logList = [now.strftime('%d/%m/%Y %H:%M:%S'), 'MAIN']
        logList.append(''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)).replace('\n',' --- ').replace('\t',' -- '))
        f.write(', '.join(logList) + '\n')

while True:
    try:
        try:
            sniff = Dave()
        except Exception as e:
            log_to_file(e)
            sleep(60 * 5)
            continue
        try:
            sniff.socialize()
            sleep(60 * (15 + 7 * random.random()))
        except Exception as e:
            log_to_file(e)
            sniff.log_error('MAIN - socialize()', exception=e)
        try:
            sniff.drop_them()
        except Exception as e:
            log_to_file(e)
            sniff.log_error('MAIN - drop_them()', exception=e)
        
        if is_time_between(time(11,00), time(14,30)) or is_time_between(time(18,00), time(21,30)):
            sleep(60 * (15 + 3 * random.random()))
            try:
                sniff.make_friends()
            except Exception as e:
                log_to_file(e)
                sniff.log_error('MAIN - make_friends()', exception=e)
        elif is_time_between(time(00,00), time(3,20)):
            try:
                sniff.load_collectors()
            except Exception as e:
                log_to_file(e)
                sniff.log_error('MAIN - load_collectors()', exception=e)
    except Exception as e:
        log_to_file(e)

    sleep(60 * 60 * (2 + random.random()) - 60 * 15)
