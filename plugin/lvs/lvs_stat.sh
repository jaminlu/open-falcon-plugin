#!/bin/bash
#Created on 2017/5/22


# 获取lvs的状态信息
/sbin/ipvsadm -Ln --rate | grep -v -e '\->' -e 'Prot' -e 'Virtual' > /tmp/lvs.stats

# 每秒的连接数
TOTAL_CPS=$(awk '{sum += $3};END {print sum}' /tmp/lvs.stats)

# 每秒的入包数
TOTAL_InPPS=$(awk '{sum += $4};END {print sum}' /tmp/lvs.stats)

# 每秒的出包数
TOTAL_OutPPS=$(awk '{sum += $5};END {print sum}' /tmp/lvs.stats)

# 每秒的入字节数
TOTAL_InBPS=$(awk '{sum += $6};END {print sum}' /tmp/lvs.stats)

# 每秒的出字节数
TOTAL_OutBPS=$(awk '{sum += $7};END {print sum}' /tmp/lvs.stats)

echo "total.conns ${TOTAL_CPS}"
echo "in.packets ${TOTAL_InPPS}"
echo "out.packets ${TOTAL_OutPPS}"
echo "in.bytes ${TOTAL_InBPS}"
echo "out.bytes ${TOTAL_OutBPS}"
