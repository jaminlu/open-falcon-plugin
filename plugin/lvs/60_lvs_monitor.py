#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
Created on 2017/5/22
'''

import shell
import os
import time

try:
    import json
except:
    import simplejson as json

ENDPOINT = os.uname()[1]
PATH = os.path.split(os.path.realpath(__file__))[0]
my_script = "bash " + PATH + "/lvs_stat.sh"


def lvsStat():
    ret = []
    ts=int(time.time())
    try:
        sh = shell.Shell()
        sh.run(my_script)
        if sh.code == 0:
            lvs_total_stat = sh.output()
            for s in lvs_total_stat:
                s = s.strip().split()
                metric = {
                    "endpoint": ENDPOINT,
                    "metric": "lvs.%s" % s[0].lower(),
                    "tags": "",
                    "timestamp": ts,
                    "value": s[1],
                    "step": 60,
                    "counterType": "GAUGE"
                }
                ret.append(metric)

            fp = open('/tmp/lvs.stats','r')
            for line in fp:
                line = line.strip().split()
                protocal = line[0]
                vip = line[1]

                vip_cps = line[2]
                vip_cps_metrics = {
                    "endpoint": ENDPOINT,
                    "metric": "lvs.vip.conns",
                    "tags": "protocal=%s, vip=%s" % (protocal, vip),
                    "timestamp": ts,
                    "value": vip_cps,
                    "step": 60,
                    "counterType": "GAUGE"
                }
                ret.append(vip_cps_metrics)

                vip_in_pps = line[3]
                vip_in_pps_metrics = {
                    "endpoint": ENDPOINT,
                    "metric": "lvs.vip.inpkts",
                    "tags": "protocal=%s, vip=%s" % (protocal, vip),
                    "timestamp": ts,
                    "value": vip_in_pps,
                    "step": 60,
                    "counterType": "GAUGE"
                }
                ret.append(vip_in_pps_metrics)

                vip_out_pps = line[4]
                vip_out_pps_metrics = {
                    "endpoint": ENDPOINT,
                    "metric": "lvs.vip.outpkts",
                    "tags": "protocal=%s, vip=%s" % (protocal, vip),
                    "timestamp": ts,
                    "value": vip_out_pps,
                    "step": 60,
                    "counterType": "GAUGE"
                }
                ret.append(vip_out_pps_metrics)

                vip_in_bps = line[5]
                vip_in_bps_metrics = {
                    "endpoint": ENDPOINT,
                    "metric": "lvs.vip.inbytes",
                    "tags": "protocal=%s, vip=%s" % (protocal, vip),
                    "timestamp": ts,
                    "value": vip_in_bps,
                    "step": 60,
                    "counterType": "GAUGE"
                }
                ret.append(vip_in_bps_metrics)

                vip_out_bps = line[6]
                vip_out_bps_metrics = {
                    "endpoint": ENDPOINT,
                    "metric": "lvs.vip.outbytes",
                    "tags": "protocal=%s, vip=%s" % (protocal, vip),
                    "timestamp": ts,
                    "value": vip_out_bps,
                    "step": 60,
                    "counterType": "GAUGE"
                }
                ret.append(vip_out_bps_metrics)
    except:
        metric = {
            "endpoint": ENDPOINT,
            "metric": "lvs.noinstall" ,
            "tags": "",
            "timestamp": ts,
            "value": 0,
            "step": 60,
            "counterType": "GAUGE"
        }
        ret.append(metric)

    return ret


def main():
    mymetrics = lvsStat()
    print(json.dumps(mymetrics, indent=4))


if __name__ == '__main__':
    main()

