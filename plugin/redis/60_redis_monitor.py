#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
Created on 2017/5/23
'''

import redis
import time
import os
import random
import re

try:
    import json
except:
    import simplejson as json


ENDPOINT = os.uname()[1]


redis_metric_dict = {
            "total_connections_received": "COUNTER",
            "rejected_connections": "COUNTER",
            "connected_clients": "GAUGE",
            "blocked_clients": "GAUGE",

            "used_memory": "GAUGE",
            "used_memory_rss": "GAUGE",
            "mem_fragmentation_ratio": "GAUGE",

            "expired_keys": "COUNTER",
            "evicted_keys": "COUNTER",
            "keyspace_hits": "COUNTER",
            "keyspace_misses": "COUNTER",
            "keyspace_hit_ratio": "GAUGE",  #keyspace_hits/(keyspace_hits+keyspace_misses)

            "total_commands_processed": "COUNTER",

            "total_net_input_bytes": "COUNTER",
            "total_net_output_bytes": "COUNTER",

            "expired_keys": "COUNTER",
            "evicted_keys": "COUNTER",

            "used_cpu_sys": "COUNTER",
            "used_cpu_user": "COUNTER",

            "slowlog_len": "COUNTER",
        }


class RedisStat(object):
    def __init__(self,host,port,passwd=None, db=15 ,step=60):
        self.host = host
        self.port = port
        self.passwd = passwd
        self.db = db
        self.step = step
        self.ts = int(time.time())

        try:
            self.conn = redis.Redis(host=self.host,port=self.port,password=self.passwd)
            self.judge = True
            self.rds_stat = self.__redis_stat()
        except Exception,e:
            self.judge = False

    def __redis_stat(self):
        return self.conn.info()

    def __redis_slowlog_stat(self):
        ret = []
        slowlog_len_metric = {
            "endpoint": ENDPOINT,
            "metric": "redis.slowlog_len",
            "tags": "port=%s" % self.port,
            "timestamp": self.ts,
            "value": self.conn.slowlog_len(),
            "step": self.step,
            "counterType": "GAUGE"
        }
        ret.append(slowlog_len_metric)

        return ret

    def __redis_cmd_stat(self):
        ret = []
        cmd_stats =  self.conn.info('commandstats')
        for k,v in cmd_stats.items():
            cmd_metric = {
                "endpoint": ENDPOINT,
                "metric": "redis.%s.usec_per_call" % k,
                "tags": "port=%s" % self.port,
                "timestamp": self.ts,
                "value": v['usec_per_call'],
                "step": self.step,
                "counterType": "GAUGE"
            }
            ret.append(cmd_metric)

        return ret

    def __redis_alive(self):
        redis_is_alive = 0
        if self.judge:
            # redis.ping监控存活
            redis_ping = self.conn.ping()

            # hset,hget监控可用性
            self.conn.hset('xl_monitor','xl_monitor_redis','xl_monitor_redis_%s' % random.randint(10000,1000000))
            redis_hget_ret = self.conn.hget('xl_monitor','xl_monitor_redis')

            if redis_ping and redis_hget_ret:
                redis_is_alive = 1

            redis_is_alive_ret = {
                "endpoint": ENDPOINT,
                "metric": "redis.alive",
                "tags": "port=%s" % self.port,
                "timestamp": self.ts,
                "value": redis_is_alive,
                "step": self.step,
                "counterType": "GAUGE"
            }
        else:
            redis_is_alive_ret = {
                "endpoint": ENDPOINT,
                "metric": "redis.alive",
                "tags": "port=%s" % self.port,
                "timestamp": self.ts,
                "value": redis_is_alive,
                "step": self.step,
                "counterType": "GAUGE"
            }

        return redis_is_alive_ret

    def __redis_collect_stat(self):
        redis_stat_ret = []

        total_keyspace = self.rds_stat['keyspace_hits']+self.rds_stat['keyspace_misses']
        hits_keyspace = self.rds_stat['keyspace_hits']
        
        if total_keyspace:
            keyspace_hit_ratio = float(hits_keyspace) / total_keyspace
        else:
            keyspace_hit_ratio = 0

        keyspace_hit_ratio_metric =  {
            "endpoint": ENDPOINT,
            "metric": "redis.keyspace_hit_ratio",
            "tags": "port=%s" % self.port,
            "timestamp": self.ts,
            "value": keyspace_hit_ratio,
            "step": self.step,
            "counterType": "GAUGE"
        }

        redis_stat_ret.append(keyspace_hit_ratio_metric)

        for k,v in self.rds_stat.items():
            if k in redis_metric_dict.keys():
                if k == 'keyspace_hit_ratio':
                    pass
                else:
                    redis_metric_falcon = {
                        "endpoint": ENDPOINT,
                        "metric": "redis.%s" % k,
                        "tags": "port=%s" % self.port,
                        "timestamp": self.ts,
                        "value": self.rds_stat[k],
                        "step": self.step,
                        "counterType": "%s" % redis_metric_dict[k]
                    }

                redis_stat_ret.append(redis_metric_falcon)

        return redis_stat_ret

    def redis_falcon_data(self):
        redis_falcon_stat = []
        redis_falcon_stat.append(self.__redis_alive())
        if self.judge:
            redis_falcon_stat = redis_falcon_stat + self.__redis_collect_stat() + self.__redis_slowlog_stat() + self.__redis_cmd_stat()
        else:
            redis_falcon_stat = redis_falcon_stat

        return redis_falcon_stat


REDIS_CONF_DIR = ["/usr/local/redis/conf","/usr/local/redis/etc"]


def redis_conf_parse():
    ret = []
    for conf_dir in REDIS_CONF_DIR:
        if os.path.isdir(conf_dir):
            for conf in os.listdir(conf_dir):
                fp = open(conf_dir+'/'+conf, 'r')
                redis_pwd = None
                redis_port = None
                for s in fp:
                    if re.search('requirepass', s):
                        if s.startswith('requirepass'):
                            redis_pwd = s.strip().split()[1]
                        else:
                            redis_pwd=None

                    if re.search('port', s) and s.startswith('port'):
                        redis_port = s.strip().split()[1]
                    if re.search('bind',s) and s.startswith('bind'):
                        redis_ip = s.split('bind')[1].strip().split()
                fp.close()
                
                ret.append({'redis_ip': redis_ip, 'redis_pwd': redis_pwd, 'redis_port': int(redis_port)})

    return ret


def main():
    redis_conf_info = redis_conf_parse()
    if redis_conf_info:
        mymetrics = []
        for redis_conf in redis_conf_info:
            redis_host = redis_conf['redis_ip'][0]
            redis_port = redis_conf['redis_port']

            if redis_conf['redis_pwd']:
                redis_pwd = redis_conf['redis_pwd']
                redis_stat = RedisStat(redis_host,redis_port,redis_pwd)
            else:
                redis_stat = RedisStat(redis_host,redis_port)

            mymetrics += redis_stat.redis_falcon_data()

        print(json.dumps(mymetrics,indent=4))
    else:
        mymetrics = {
            "endpoint": ENDPOINT,
            "metric": "redis.alive",
            "tags": "port=%s" % 6379,
            "timestamp": int(time.time()),
            "value": 2,
            "step": 60,
            "counterType": "GAUGE"
        }
        print(json.dumps(mymetrics,indent=4))


if __name__ == '__main__':
    main()



