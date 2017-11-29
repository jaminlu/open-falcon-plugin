#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
author:captainj
'''

import os
import time
from config import dbconfs

try:
    import json
except:
    import simplejson as json


mysql_conn_metric_dict = {
    'max_connections': 'GAUGE',
    'Threads_connected': 'GAUGE',
    'connected_rate': 'GAUGE',
}

mysql_comm_metric_dict = {
    'Aborted_connects': 'COUNTER', # 客户端不能正常连接，失败的连接数量
    'Aborted_clients': 'COUNTER',  # 客户端中断数量，可能有恶意连接
    'Slow_queries': 'COUNTER',
    'Select_scan': 'COUNTER',
    'Select_full_join': 'COUNTER',
    'Sort_scan': 'COUNTER',
    'Com_select': 'COUNTER',
    'Com_update': 'COUNTER',
    'Com_insert': 'COUNTER',
    'Com_delete': 'COUNTER',
}

mysql_slave_metric_dict = {
    'Slave_IO_Running': 'GAUGE',
    'Slave_SQL_Running': 'GAUGE',
    'Seconds_Behind_Master': 'GAUGE',
}


ENDPOINT = os.uname()[1]


class MysqlStat(object):
    def __init__(self, dbconf, step=60):
        self.dbconf = dbconf
        self.port = dbconf['port']
        self.host = dbconf['host']
        self.step = step
        self.ts = int(time.time())

        try:
            try:
                import pymysql
                self.mydriver = pymysql.__name__
                self._conn = pymysql.connect(host=self.dbconf['host'],
                                         user=self.dbconf['user'],
                                         password=self.dbconf['password'],
                                         port=self.dbconf['port'],
                                         charset=self.dbconf['charset'],
                                         connect_timeout=1,
                                     )
            except:
                import MySQLdb
                self.mydriver = MySQLdb.__name__
                self._conn = MySQLdb.connect(host=self.dbconf['host'],
                                         user=self.dbconf['user'],
                                         passwd=self.dbconf['password'],
                                         port=self.dbconf['port'],
                                         charset=self.dbconf['charset'],
                                         connect_timeout=1,
                                     )
            self._cur = self._conn.cursor()
            self.judge = True
            self.mysql_ver = self._mysql_version()
        except:
            self.judge = False

    def ping(self):
        if self.mydriver == 'pymysql':
            return self._conn.ping()
        else:
            return self._mysql_version()

    def query(self, sql):
        try:
            self._cur.execute("SET NAMES utf8")
            self._cur.execute(sql)
            result = self._cur.fetchall()
            return result
        except Exception, e:
            print e

    def _mysql_version(self):
        return int(self.query('select version();')[0][0].split('.')[0])

    def __del__(self):
        try:
            self._cur.close()
            self._conn.close()
        except:
            pass

    def close(self):
        self.__del__()

    def _mysql_stat(self):
        if self.mysql_ver == 4:
            return self.query('show status')
        else:
            return self.query('show global status')

    def _mysql_variables(self):
        return self.query('show global variables')

    def _mysql_ping(self):
        #mysql_alive = 0
        if self.ping():
            mysql_alive = 1
        else:
            mysql_alive = 0

        return mysql_alive

    def _mysql_slave_stat(self):
        return self.query("show slave status")

    def mysql_falcon_data(self):
        ret = []
        if self.judge:
            mysql_stat_ret = self._mysql_stat()
            mysql_variables_ret = self._mysql_variables()
            mysql_is_alive = self._mysql_ping()

            mysql_is_alive_ret = {
                "endpoint": ENDPOINT,
                "metric": "mysql.alive",
                "tags": "port=%s, host=%s" % (self.port,self.host),
                "timestamp": self.ts,
                "value": mysql_is_alive,
                "step": self.step,
                "counterType": "GAUGE"
            }
            ret.append(mysql_is_alive_ret)

            if self.mysql_ver == 4:
                queries_ret = [mysql_stat[1] for mysql_stat in mysql_stat_ret if mysql_stat[0] == 'Questions'][0]
            else:
                queries_ret = [mysql_stat[1] for mysql_stat in mysql_stat_ret if mysql_stat[0] == 'Queries'][0]
            mysql_qps = {
                "endpoint": ENDPOINT,
                "metric": "mysql.qps",
                "tags": "port=%s, host=%s" % (self.port,self.host),
                "timestamp": self.ts,
                "value": queries_ret,
                "step": self.step,
                "counterType": "COUNTER"
            }
            ret.append(mysql_qps)

            max_connections_ret = [ mysql_var[1] for mysql_var in mysql_variables_ret if mysql_var[0] == 'max_connections' ][0]
            mysql_max_connections = {
                "endpoint": ENDPOINT,
                "metric": "mysql.max_connections",
                "tags": "port=%s, host=%s" % (self.port,self.host),
                "timestamp": self.ts,
                "value": max_connections_ret,
                "step": self.step,
                "counterType": "GAUGE"
            }
            ret.append(mysql_max_connections)

            threads_connected_ret = [ mysql_stat[1] for mysql_stat in mysql_stat_ret if mysql_stat[0] == 'Threads_connected' ][0]
            mysql_threads_connected = {
                "endpoint": ENDPOINT,
                "metric": "mysql.threads_connected",
                "tags": "port=%s, host=%s" % (self.port,self.host),
                "timestamp": self.ts,
                "value": threads_connected_ret,
                "step": self.step,
                "counterType": "GAUGE"
            }
            ret.append(mysql_threads_connected)

            mysql_connected_rate = {
                "endpoint": ENDPOINT,
                "metric": "mysql.connected_rate",
                "tags": "port=%s, host=%s" % (self.port,self.host),
                "timestamp": self.ts,
                "value": int(float(threads_connected_ret)/int(max_connections_ret)*100),
                "step": self.step,
                "counterType": "GAUGE"
            }
            ret.append(mysql_connected_rate)

            for k, v in mysql_comm_metric_dict.items():
                comm_ret =  [ mysql_stat[1] for mysql_stat in mysql_stat_ret if mysql_stat[0] == k ][0]
                mysql_comm_metric = {
                    "endpoint": ENDPOINT,
                    "metric": "mysql.%s" % k.lower(),
                    "tags": "port=%s, host=%s" % (self.port,self.host),
                    "timestamp": self.ts,
                    "value": comm_ret,
                    "step": self.step,
                    "counterType": v
                }
                ret.append(mysql_comm_metric)

            mysql_slave_stat = self._mysql_slave_stat()

            # slave切换成master的情况, 这种情况下，请注意，最好通过RESET SLAVE ALL,清理对应的信息，避免影响监控,导致误报
            if mysql_slave_stat:
                master_host = mysql_slave_stat[0][1]
                slave_io_running = mysql_slave_stat[0][10]
                slave_sql_running = mysql_slave_stat[0][11]
                seconds_behind_master = mysql_slave_stat[0][32]

                if slave_io_running == 'Yes':
                    mysql_slave_io_running_metrics = {
                        "endpoint": ENDPOINT,
                        "metric": "mysql.slave_io_running",
                        "tags": "port=%s, host=%s, master=%s, role=slave" % (self.port,self.host,master_host),
                        "timestamp": self.ts,
                        "value": 1,
                        "step": self.step,
                        "counterType": "GAUGE"
                    }
                else:
                    mysql_slave_io_running_metrics = {
                        "endpoint": ENDPOINT,
                        "metric": "mysql.slave_io_running",
                        "tags": "port=%s, host=%s, master=%s, role=slave" % (self.port,self.host,master_host),
                        "timestamp": self.ts,
                        "value": 0,
                        "step": self.step,
                        "counterType": "GAUGE"
                    }
                ret.append(mysql_slave_io_running_metrics)

                if slave_sql_running == 'Yes':
                    mysql_slave_sql_running_metrics = {
                        "endpoint": ENDPOINT,
                        "metric": "mysql.slave_sql_running",
                        "tags": "port=%s, host=%s, master=%s, role=slave" % (self.port,self.host,master_host),
                        "timestamp": self.ts,
                        "value": 1,
                        "step": self.step,
                        "counterType": "GAUGE"
                    }
                else:
                    mysql_slave_sql_running_metrics = {
                        "endpoint": ENDPOINT,
                        "metric": "mysql.slave_sql_running",
                        "tags": "port=%s, host=%s, master=%s, role=slave" % (self.port,self.host,master_host),
                        "timestamp": self.ts,
                        "value": 0,
                        "step": self.step,
                        "counterType": "GAUGE"
                    }
                ret.append(mysql_slave_sql_running_metrics)

                mysql_seconds_behind_master_metrics = {
                    "endpoint": ENDPOINT,
                    "metric": "mysql.seconds_behind_master",
                    "tags": "port=%s, host=%s, master=%s, role=slave" % (self.port,self.host,master_host),
                    "timestamp": self.ts,
                    "value": seconds_behind_master,
                    "step": self.step,
                    "counterType": "GAUGE"
                }
                ret.append(mysql_seconds_behind_master_metrics)
        else:
            mysql_is_alive = 0
            mysql_is_alive_ret = {
                "endpoint": ENDPOINT,
                "metric": "mysql.alive",
                "tags": "port=%s, host=%s" % (self.port,self.host),
                "timestamp": self.ts,
                "value": mysql_is_alive,
                "step": self.step,
                "counterType": "GAUGE"
            }

            ret.append(mysql_is_alive_ret)

        self.close()

        return ret


def main():
    mymetrics = []
    for dbconf in dbconfs:
        mysql_stat_obj = MysqlStat(dbconf)
        mymetrics += mysql_stat_obj.mysql_falcon_data()

    print(json.dumps(mymetrics,indent=4))


if __name__ == '__main__':
    main()











