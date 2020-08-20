import configparser
import psutil
import sys
import time
import threading
from datetime import datetime, timedelta
import socket
import requests


def main(device="", threshold=0):
    if device == "" and threshold == 0:
        conf = configparser.ConfigParser()
        conf.read('conf.ini')
        device = conf['main']['device']
        threshold = float(conf['main']['threshold'])

        alert = conf['mail']['alert']
        mail_api = conf['mail']['api']
        mail_target = conf['mail']['target']
        mail_interval = conf['mail']['interval']

        hostname = str(socket.gethostname())
        if alert != "True" and alert != "False":
            print("Missing mail.alert setting in conf.ini")
            exit()
        if alert == "True":
            alert = True
            if mail_api == "":
                print("Missing mail.api setting in conf.ini")
                exit()
            if mail_target == "":
                print("Missing mail.target setting in conf.ini")
                exit()
            if mail_interval == "":
                print("Missing mail.interval setting in conf.ini")
                exit()
            else:
                mail_interval = int(mail_interval)

        else:
            alert = False

    mail_last_send = None

    while True:
        old_info = check_device(psutil.net_io_counters(pernic=True), device)
        time.sleep(1)
        new_info = check_device(psutil.net_io_counters(pernic=True), device)
        bandwidth = (new_info - old_info)/1024/1024
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(now_time + " - " + str(bandwidth) + " MB/s")
        if alert and bandwidth > threshold:
            if mail_last_send is None or mail_last_send < datetime.now():
                subject = "%s 頻寬異常警告" % hostname
                title = now_time
                content = "主機: %s<br>時間: %s<br>閥值: %s MB/s<br>超標: <span style='color:red'>%s</span> MB/s<br>" % (hostname, now_time, threshold, bandwidth)
                # content = "test"
                main_job = threading.Thread(target=mail_job(mail_api, mail_target, subject, title, content))
                main_job.start()
                mail_last_send = datetime.now()+timedelta(minutes=mail_interval)



def check_device(info, device):
    if device not in info:
        print("device " + device + " gone")
        exit()
    else:
        return info[device].bytes_sent

def mail_job(api, target, subject, title, content):
    headers = {"Content-Type": "application/json", "charset": "utf-8"}
    body = '{"mailer_target": "%s","mailer_subject": "%s", "mailer_title": "%s", "mailer_content": "%s"}' % (target, subject, title, content)
    body = body.encode('utf-8')
    response = requests.post(api, headers=headers, data=body)
    if response.status_code == 201:
        print('Email alert sent.')
    else:
        print('Email alert error!!!')
        error_response = response.content
        print(error_response)

if(len(sys.argv) > 1):
    if sys.argv[1]:
        main(sys.argv[1])
else:
    main()
