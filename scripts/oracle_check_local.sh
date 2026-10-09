#!/bin/bash
LANG=C
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
source /etc/profile

YELLOW="$(printf '\033[1;33m')"
GREEN="$(printf '\033[1;32m')"
LIGHTGREEN="$(printf '\033[0;32m')"
RED="$(printf '\033[1;31m')"
CYAN="$(printf '\033[0;36m')"
LIGHTBLUE="$(printf '\033[0;94m')"
BROWN="$(printf '\033[0;33m')"
NORMAL="$(printf '\033[0m')"


# 插入节点标记
InsertNode(){
    echo " ${YELLOW}*${NORMAL} ${RED}[$(date "+%Y-%m-%d %H:%M:%S")]${NORMAL}${CYAN}[$$]${NORMAL} "
}

# 用户输入信息
UserInput() {
    STATUS=1
    while [ ${STATUS} -eq 1 ]; do
        read -p "$(InsertNode)${LIGHTBLUE}$1: ${NORMAL}" $2
        STATUS=$?
    done
}

GetDistroInfo(){
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_NAME="$ID"
        DISTRO_VERSION="$VERSION_ID"
        DISTRO_CODE="$VERSION_CODENAME"
        [ -z "$DISTRO_CODE" ] && DISTRO_CODE=$(echo "$VERSION_ID" | sed -E 's/.*\((.+)\)/\1/')
        case "$DISTRO_NAME" in
            rhel) DISTRO_NAME="Red Hat Enterprise Linux";;
            centos) DISTRO_NAME="CentOS";;
            anolis) DISTRO_NAME="Anolis";;
            ubuntu) DISTRO_NAME="Ubuntu";;
            oracle) DISTRO_NAME="Oracle Linux";;
        esac
    else
        if command -v lsb_release >/dev/null 2>&1; then
            DISTRO_NAME=$(lsb_release -is)
            DISTRO_VERSION=$(lsb_release -rs)
            DISTRO_CODE=$(lsb_release -cs)
        else
            DISTRO_NAME="Unknown"
            DISTRO_VERSION="Unknown"
            DISTRO_CODE="Unknown"
        fi
    fi
}  

# 命令检查
CommandCheck(){
    if which python >/dev/null 2>&1;then
        python=python
    elif which python3 >/dev/null 2>&1;then
        python=python3
    else
        echo "${RED}Python / python3 command not found.${NORMAL}"
        exit 2
    fi
    su - $ORACLE_USER -c "which sqlplus >/dev/null 2>&1"
    if [ $? -ne 0 ];then echo "${RED}($ORACLE_USER)sqlplus command not found.${NORMAL}";exit 2;fi
    su - $ORACLE_USER -c "which lsnrctl >/dev/null 2>&1"
    if [ $? -ne 0 ];then echo "${RED}($ORACLE_USER)lsnrctl command not found.${NORMAL}";exit 2;fi
}

# OS 检查
OsCheck(){
    GetDistroInfo
    if echo ${DISTRO_NAME} | grep -Eqvi "Anolis|CentOS|Ubuntu|Red|Oracle"; then
        echo "${RED}Error: This script is only applicable to Anolis/redhat/centos/ubuntu/Oracle Linux!${NORMAL}"
        exit 2
    fi
    DistroName="$DISTRO_NAME"
}

# root检查
CheckRoot(){
    if [ $(id -u) != "0" ]; then
        echo "${RED}Error: You must use root to run this script. Please switch to root!${NORMAL}"
        exit 2
    fi
}

# oracle用户检查
CheckOracle(){
    :
}

# 获取项目名称和资产ID号
GetProjectNameAndAssetId(){
    if [ ! -s "/etc/assetname" ]; then
        echo "${RED}Please fill in the asset information to /etc/assetname first.${NORMAL}"
        echo "${RED}Examples：project name-system name-192.168.0.1${NORMAL}"
        exit 2
    else
        PROJECTNAME=$(awk -F "-" '{print $1}' /etc/assetname)
        ASSETID=$(cat /etc/assetname | sha256sum | awk '{print $1}')
        echo "$(InsertNode)${GREEN}PROJECTNAME:            ${PROJECTNAME}${NORMAL}"
        echo "$(InsertNode)${GREEN}ASSET ID:          ${ASSETID}${NORMAL}"
    fi
}

# 获取 Oracle 用户
GetOracleUser() {
    if id "oracle" >/dev/null 2>&1; then
        ORACLE_USER="oracle"
    elif id "oracle12c" >/dev/null 2>&1; then
        ORACLE_USER="oracle12c"
    else
        echo "${RED}Error: Neither 'oracle' nor 'oracle12c' user exists.${NORMAL}"
        exit 2
    fi
    echo "$(InsertNode)${GREEN}Using Oracle user: ${ORACLE_USER}${NORMAL}"
}

# 确定连接数据库时使用的命令。例如： sqlplus / as sysdba。
sqlpluscmd_check_fun() {
sqlpluscmd_check(){
sqlpluscmd_check_status=`su - $ORACLE_USER -c "$sqlpluscmd << EOF
set pagesize 0
set heading off
set feedback off
set tab off
select 1 from dual;
EOF
" | awk 'END{if($NF!=1){print 0}else{print $NF}}'`
}
sqlpluscmd='sqlplus -s / as sysdba'
sqlpluscmd_check

if [ $sqlpluscmd_check_status -eq 0 ];then
  echo "Unable to login to the database by \"sqlplus / as sysdba\""
  while :
  do
      UserInput "Please enter the command to connect to the database: sqlplus " "CHOOSE_STR"
      sqlpluscmd="sqlplus -s $CHOOSE_STR"
      sqlpluscmd_check
      if [ $sqlpluscmd_check_status -eq 1 ];then
        break
      fi
  done
fi
}

# sql 输出格式化
sqlcmd1() {
su - $ORACLE_USER -c "$sqlpluscmd << EOF
set linesize 200
set pagesize 1000
set pagesize 0
set heading off
set feedback off
set tab off
$sql
EOF"
}
sqlcmd2() {
su - $ORACLE_USER -c "$sqlpluscmd << EOF
set pagesize 1000
set linesize 200
set feedback off
set tab off
set serverout on
$sql
EOF"
}

########################################################################################################################
# 生成 XML 文件
# 收集数据
GenerateXml(){
    StartElement() {
        echo "<$1>"
    }
    StartSectionElement() {
        echo "<section id=\"$1\">"
    }
    StartMemberElement() {
        echo "<member key=\"$1\">"
    }
    StartNodeElement() {
        echo "<node key=\"$1\">"
    }
    EndElement() {
        echo "</$1>"
    }

    # 1 开始
    printf '\xEF\xBB\xBF'      # 添加 BOM
    echo '<?xml version="1.0" encoding="utf-8"?>'
    StartElement "systemchecklog"

    StartElement "project"
    awk -F- '{print($1);}' /etc/assetname
    EndElement "project"

    StartElement "application"
    awk -F- '{print($2);}' /etc/assetname
    EndElement "application"

    StartElement "assetid"
    cat /etc/assetname|sha256sum|awk '{print($1);}'
    EndElement "assetid"


    # 2 OS 信息
    StartSectionElement "OS Info"

    StartMemberElement "os type"
    echo ${DistroName}
    EndElement "member"

    StartMemberElement "os version"
    echo "${DISTRO_VERSION:-unknown}"
    EndElement "member"

    StartMemberElement "issuing code"
    echo "${DISTRO_CODE:-unknown}"
    EndElement "member"

    StartMemberElement "architecture"
    uname -i
    EndElement "member"

    StartMemberElement "kernel version"
    uname -r
    EndElement "member"

    StartMemberElement "manufacturer"
    dmidecode -s system-manufacturer
    EndElement "member"

    StartMemberElement "model"
    dmidecode -s system-product-name
    EndElement "member"

    StartMemberElement "hostname"
    hostname
    EndElement "member"

    StartMemberElement "ip address"
    hostname -I 2>/dev/null || hostname -i
    EndElement "member"

    StartMemberElement "gateway"
    ip route show | awk '/^default/{print $3}'
    EndElement "member"

    StartMemberElement "dns"
    echo ""`awk '/^nameserver/{print($2);}' /etc/resolv.conf`""
    EndElement "member"

    StartMemberElement "mac address"
    echo "`for net in $(ls /sys/class/net/);do echo|awk -v NET=$net '{print(NET": "$0)}' /sys/class/net/$net/address;done`"
    EndElement "member"

    EndElement "section"


    # 3 系统状态
    StartSectionElement "System Status"

    StartMemberElement "connect netowrk status"
    if echo `ping -c1 baidu.com 2>&1` | grep -q "unknown host"; then echo no;else echo yes;fi
    EndElement "member"

    StartMemberElement "lang"
    if [ -s /etc/locale.conf ];then
		    cat /etc/locale.conf |  awk -F'"' '/^LANG=/{print $2}'
	  elif [ -s /etc/sysconfig/i18n ];then
		    cat /etc/sysconfig/i18n |  awk -F'"' '/^LANG=/{print $2}'
		elif [ -s /etc/default/locale ];then
		    cat /etc/default/locale | awk -F'"' '/^LANG=/{print $2}'
	  fi
    EndElement "member"

    StartMemberElement "iptables status"
    case ${DistroName} in
        "Anolis"|"Centos"|"CentOS Linux"|"Red Hat Enterprise Linux Server"|"Oracle Linux Server")
            if which systemctl > /dev/null 2>&1;then
                if systemctl status firewalld > /dev/null 2>&1;then echo "enable";else echo "disable";fi
            else
                if service iptables status > /dev/null 2>&1;then echo "enable";else echo "disable";fi
            fi
            ;;
        "Ubuntu")
            if ufw status | grep -q inactive;then echo "disable";else echo "enable";fi
    esac
    EndElement "member"

    StartMemberElement "selinux status"
    if echo ${DistroName} | grep -qE "CentOS|Red|Oracle|Anolis";then getenforce;else echo "---";fi
    EndElement "member"

    StartMemberElement "system boot time"
    date -d "$(awk -F. '{print $1}' /proc/uptime) second ago" +"%F %T"
    EndElement "member"

    StartMemberElement "system now time"
    date '+%F %T'
    EndElement "member"

    StartMemberElement "system up time"
	  cat /proc/uptime| awk -F. '{run_days=$1 / 86400;run_hour=($1 % 86400)/3600;run_minute=($1 % 3600)/60;run_second=$1 % 60;printf("%d days, %d:%d:%d\n",run_days,run_hour,run_minute,run_second)}'
    EndElement "member"

    StartMemberElement "system load"
    awk '{print($1,$2,$3);}' /proc/loadavg
    EndElement "member"

    EndElement "section"


    # 4 内存信息
    StartSectionElement "Memory Info"

    StartMemberElement "memory total"
    awk '{if(/MemTotal/){total=$2;}}END{printf("%.2f%s\n",total/1048576,"GB");}' /proc/meminfo
    EndElement "member"

    StartMemberElement "system memory used"
    awk '{if(/MemTotal/){total=$2;}else if(/MemFree/){free=$2;}}END{print ((total-free)/total)*100"%";}' /proc/meminfo
    EndElement "member"

    StartMemberElement "app memory used"
    awk '{if(/MemTotal/){total=$2;}else if(/MemFree/){free=$2;}else if(/Buffers/){buffers=$2;}else if(/^Cached/){cached=$2;}}END{print ((total-(free+buffers+cached))/total)*100"%";}' /proc/meminfo
    EndElement "member"

    StartMemberElement "Swap Info"
    if [ $(swapon -s | wc -l) -eq 0 ];then echo no ;else echo yes;fi
    EndElement "member"

    EndElement "section"


    # 5 CPU 信息
    StartSectionElement "CPU Info"

    #物理
    StartMemberElement "cpu physical"
    cat /proc/cpuinfo | grep "physical id" | sort -rn | uniq | wc -l
    EndElement "member"

    #核心
    StartMemberElement "cpu cores"
    awk '{if(/^cpu cores/){NUM=$4;}} END{print(NUM);}' /proc/cpuinfo
    EndElement "member"

    #线程
    StartMemberElement "cpu processor"
    awk '{if(/^processor/){NUM=$3;}} END{print(NUM+1);}' /proc/cpuinfo
    EndElement "member"

    StartMemberElement "cpu model"
    awk '{if(/^model name/ && NR<10){print(substr($0,14));}}' /proc/cpuinfo
    EndElement "member"

    StartMemberElement "cpu used"
    top -bin 1|awk '{if(/Cpu\(s\)/){print(substr($0,10));}}'
    EndElement "member"

    EndElement "section"

    # 6 磁盘/IO 信息
    StartSectionElement "DISK/IO Info"

    StartMemberElement "disk"
    DISK=$(lsblk 2>/dev/null|grep "disk"|grep -Ee "^[a-z]{3,}.*[GT]|^-[a-z]{3}\s.*[GT]"|awk '{print($1,$4);}'|awk 'BEGIN{ORS=" | "}{print $0}' | sed 's/...$//')
    if [[ ${DISK} == "" ]]; then
        DISK=$(fdisk -l 2>/dev/null|grep -Ev "loop|mapper"|grep -Eoe "Disk /dev/[a-z]{3}.*B"|sed 's#/dev/##g'|awk 'BEGIN{ORS=" | "}{print $0}' | sed 's/...$//')
    fi
    echo ${DISK}
    EndElement "member"

    StartMemberElement "disk and partition info"
    lsblk 2>/dev/null || fdisk -l
    EndElement "member"

    StartMemberElement "mount info"
    cat /proc/mounts
    EndElement "member"

    StartMemberElement "disk used"
    df -hP | grep "^/" | grep -Ev "/dev/loop"
    EndElement "member"

    StartMemberElement "disk used human"
    df -hP | grep "^/" | grep -Ev "/dev/loop" |awk '/%/{print($NF,$(NF-4),$(NF-3),"Use%:"$(NF-1));}'
    EndElement "member"

    StartMemberElement "inodes used"
    df -ihP | grep "^/" | grep -Ev "/dev/loop"
    EndElement "member"

    StartMemberElement "inodes used human"
    df -ihP | grep "^/" | grep -Ev "/dev/loop" |awk '/%/{print($NF,$(NF-4),$(NF-3),"Use%:"$(NF-1));}'
    EndElement "member"

    EndElement "section"


    # 6 网络信息
    StartSectionElement "Network Info"

    StartMemberElement "link status"
    if which netstat  > /dev/null 2>&1;then
        echo `netstat -ntu|awk 'BEGIN {ORS=" | "}/^tcp/ {++st[$NF]} END {for (i in st){print(i,st[i]);}}' | sed 's/...$//'`
    elif which ss  > /dev/null 2>&1;then
        echo `ss -ntu|awk '/^tcp/ {++st[$2]} END {for (i in st){print(i,st[i]);}}' | awk 'BEGIN{ORS=" | "}{print $0}' | sed 's/...$//'`
    fi
    EndElement "member"

    StartMemberElement "open ports"
    if which netstat  > /dev/null 2>&1;then
    echo ""`netstat -lntu | grep -Eo ":[0-9]{2,}" | sort -rn | uniq | awk -F: '{print $2}'`""
    elif which ss  > /dev/null 2>&1;then
        echo ""`ss -lntu | grep -Eo ":[0-9]{2,}" | sort -rn | uniq | awk -F: '{print $2}'`""
    fi
    EndElement "member"

    StartMemberElement "flow status"
    cat /proc/net/dev|sed -r 's/^ *//g'|awk -F[" ":]+ '{if(NR>2){printf("%s%s%.1f%s%s%s%s%s%.1f%s%s%s%s\n",$1," (Rx)bytes:",$2/1048576,"M"," packets:"$3," errors:"$4," dropped:"$5," (Tx)bytes:",$10/1048576,"M"," packets:"$11," errors:"$12," dropped:"$13);}}'
    EndElement "member"

    EndElement "section"


    # 7 用户信息
    StartSectionElement "User Info"

    StartMemberElement "user number"
    wc -l /etc/passwd|awk '{print($1);}'
    EndElement "member"

    StartMemberElement "user list"
    echo ""`awk -F: '{print$1}' /etc/passwd`""
    EndElement "member"

    EndElement "section"


    # 8 COURSE 信息
    StartSectionElement "Course Info"

    StartMemberElement "course status"
    top -bin 1|awk '{if(/Tasks/){print(substr($0,7));}}'
    EndElement "member"

    StartMemberElement "cpu used rank"
    ps aux|head -1;ps aux|grep -v PID|sort -rn -k +3|head -5|sed -r 's/<|&//g'
    EndElement "member"

    StartMemberElement "memory used rank"
    ps aux|head -1;ps aux|grep -v PID|sort -rn -k +4|head -5|sed -r 's/<|&//g'
    EndElement "member"

    EndElement "section"


    # 9 安全检查信息
    StartSectionElement "Security Check"

    StartMemberElement "system key files status"
    ls -ldt --full-time /etc/passwd /etc/shadow /etc/group /etc/gshadow /etc/services /etc/rc[0-9].d|awk '{print($6,$7,$9);}'
    EndElement "member"

    StartMemberElement "remote access control files"
    tail -n 5 /etc/hosts.* 2> /dev/null|sed -r 's/<|&//g'
    EndElement "member"

    StartMemberElement "local hosts file"
    cat /etc/hosts
    EndElement "member"

    EndElement "section"


    # 10 数据库信息
    StartSectionElement "Database Info"

    StartMemberElement "database name"
    sql="select name from v\\\$database;"
    sqlcmd1
    EndElement "member"

    StartMemberElement "instance name"
    sql="select instance_name from v\\\$instance;"
    sqlcmd1
    EndElement "member"

    StartMemberElement "database id"
    sql="select dbid from v\\\$database;"
    sqlcmd1
    EndElement "member"

    StartMemberElement "database version"
    sql="select version from v\\\$instance;"
    sqlcmd1
    EndElement "member"

    StartMemberElement "created time"
    sql="select to_char(created,'yyyy/mm/dd hh24:mi:ss') from v\\\$database;"
    sqlcmd1
    EndElement "member"

    StartMemberElement "character set"
    sql="select value from nls_database_parameters where parameter='NLS_CHARACTERSET';"
    sqlcmd1
    EndElement "member"

    StartMemberElement "israc"
    sql="select decode(value,'TRUE','YES','NO') IsRAC from v\\\$parameter where name='cluster_database';"
    sqlcmd1
    EndElement "member"

    EndElement "section"


    # 11 数据库详细信息
    StartSectionElement "Database Detail"

    StartMemberElement "crs status"
    sql="select decode(value,'TRUE','1','0') IsRAC from v\\\$parameter where name='cluster_database';"
    israc=`sqlcmd1`
    if [ $israc -eq 0 ];then
      echo "not a cluster"
    else
      su - grid -c "crsctl check crs"
    fi
    EndElement "member"

    StartMemberElement "cluster status"
    sql="select decode(value,'TRUE','1','0') IsRAC from v\\\$parameter where name='cluster_database';"
    israc=`sqlcmd1`
    if [ $israc -eq 0 ];then
      echo "not a cluster"
    else
      su - grid -c "crs_stat -t"
    fi
    EndElement "member"

    StartMemberElement "lsnrctl status"
    sql="select decode(value,'TRUE','1','0') IsRAC from v\\\$parameter where name='cluster_database';"
    israc=`sqlcmd1`
    if [ $israc -eq 0 ];then
      lsnrctl_user="$ORACLE_USER"
    else
      lsnrctl_user="grid"
    fi
    ORACLE_HOME1=`su - $lsnrctl_user -c "echo \\\$ORACLE_HOME"`
    for listener_name in `cat $ORACLE_HOME1/network/admin/listener.ora | awk -F"[ =]" '/^LISTENER/&&!/SCAN/{print $1}'`
    do
      su - $lsnrctl_user -c "lsnrctl status $listener_name"
    done
    EndElement "member"

    StartMemberElement "alert log"
    sql="select version from v\\\$instance;"
    database_version_num=`sqlcmd1 | awk -F. '{print $1}'`
    sql="select instance_name from v\\\$instance;"
    database_sid=`sqlcmd1`
    if [ $database_version_num -ge 11 ];then
      sql="select value From v\\\$diag_info where name='Diag Trace';"
    else
      sql="select VALUE from v\\\$parameter where name='background_dump_dest';"
    fi
    trace_log_dest=`sqlcmd1`
    tail -50 $trace_log_dest/alert_$database_sid.log 2>&1|sed -r 's/<|&/_/g'
    EndElement "member"

    StartMemberElement "opatch info"
    sql="col comp_id format a10
    col status format a10
    col version for a20
    col comments for a40
    col action for a35
    select comp_id,status,version from dba_registry;
    select action,version,comments from dba_registry_history;"
    sqlcmd2
    EndElement "member"

    StartMemberElement "sga info"
    sql="select name,value/1024/1024 mb from v\\\$sga;"
    sqlcmd2
    EndElement "member"

    StartMemberElement "controlfile info"
    sql="col name format a80
    select name from v\\\$controlfile;"
    sqlcmd2
    EndElement "member"

    StartMemberElement "log info"
    sql="col status form a10
    select GROUP#,THREAD#,SEQUENCE#,BYTES,MEMBERS,
    ARCHIVED,STATUS from v\\\$log;
    select group#,sequence#,to_char(first_time,'yyyy-mm-dd hh24:mi:ss') first_tim from v\\\$log order by first_time;
    col member form a53
    select group#,status,member from v\\\$logfile;"
    sqlcmd2
    EndElement "member"

    StartMemberElement "archive mode"
    sql="archive log list"
    sqlcmd2
    EndElement "member"

    StartMemberElement "tablespace usage"
    sql="COL TABLESPACE_NAME FORM A20
select a.tablespace_name, round(c.bytes/1024/1024,1) as Free_Size_M, a.bytes/1024/1024 as Size_M,
round((a.bytes - c.bytes)/1024/1024,1) as Used_Size_M, round(b.bytes/1024/1024 ,1) as Max_Size_M,
cast(((a.bytes - c.bytes)/a.bytes )*100 as int) as Percent_Used, cast(((a.bytes - c.bytes)/b.bytes )*100 as int ) as Percent_Max_Used
from
(select tablespace_name, sum(bytes) as bytes from dba_data_files group by tablespace_name) a,
(select tablespace_name, sum(bytes) as bytes from (
select tablespace_name, sum(bytes) as bytes from dba_data_files where autoextensible=upper('no') 
group by tablespace_name
union all
select tablespace_name, sum(maxbytes) as bytes from dba_data_files where autoextensible=upper('yes')
group by tablespace_name) group by tablespace_name) b,
(select tablespace_name, sum(bytes) as bytes from dba_free_space group by tablespace_name) c
where a.tablespace_name = b.tablespace_name(+)
and b.tablespace_name = c.tablespace_name(+)
order by 7 desc;"
    sqlcmd2
    EndElement "member"

    StartMemberElement "temp tablespace usage"
sql="select version from v\\\$instance;"
oracle_version_1=`sqlcmd1 | cut -d '.' -f 1`
if [ $oracle_version_1 -eq 10 ];then
    sql="COLUMN \"Name\" FORMAT A20;
COLUMN \"Size (M)\"FORMAT a15;
COLUMN \"HWM (M)\" FORMAT a15;
COLUMN \"HWM %\" FORMAT a15;
COLUMN \"Using (M)\" FORMAT A15;
COLUMN \"PTUSED\" FORMAT A10;
SET PAGES 200 LINES 200;
SELECT d.tablespace_name \"Name\",
   TO_CHAR(NVL(a.bytes / 1024 / 1024, 0),'99,999,990.900') \"Size (M)\",
   TO_CHAR(NVL(t.hwm, 0)/1024/1024,'99999999.999')  \"HWM (M)\",
   TO_CHAR(NVL(t.hwm / a.bytes * 100, 0), '990.00') \"HWM %\",
   TO_CHAR(NVL(t.bytes/1024/1024, 0),'99999999.999') \"Using (M)\",
   TO_CHAR(NVL(t.bytes / a.bytes * 100, 0), '990.00') \"PTUSED\"
   FROM sys.dba_tablespaces d,
                (select tablespace_name, sum(bytes) bytes from dba_temp_files group by tablespace_name) a,
                (select tablespace_name, sum(bytes_cached) hwm, sum(bytes_used) bytes from v\\\$temp_extent_pool group by tablespace_name) t
          WHERE d.tablespace_name = a.tablespace_name(+)
            AND d.tablespace_name = t.tablespace_name(+)
            AND d.extent_management like 'LOCAL'
            AND d.contents like 'TEMPORARY';"
    sqlcmd2
else
    sql="COL TABLESPACE_NAME FORM A20
select a.tablespace_name, round(c.bytes/1024/1024,1) as Free_Size_M, round(a.bytes/1024/1024,1) as Size_M,
round((a.bytes - c.bytes)/1024/1024,1) as Used_Size_M, round(b.bytes/1024/1024 ,1) as Max_Size_M,
cast(((a.bytes - c.bytes)/a.bytes )*100 as int) as Percent_Used, cast(((a.bytes - c.bytes)/b.bytes )*100 as int) as Percent_Max_Used
from
(select tablespace_name, sum(bytes) as bytes from dba_temp_files group by tablespace_name) a,
(select tablespace_name, sum(bytes) as bytes from (
select tablespace_name, sum(bytes) as bytes from dba_temp_files where autoextensible=upper('no') 
group by tablespace_name
union all
select tablespace_name, sum(maxbytes) as bytes from dba_temp_files where autoextensible=upper('yes')
group by tablespace_name) group by tablespace_name) b,
(select tablespace_name, sum(free_space) as bytes from dba_temp_free_space group by tablespace_name) c
where a.tablespace_name = b.tablespace_name(+)
and b.tablespace_name = c.tablespace_name(+)
order by 7 desc;"
    sqlcmd2
fi
    EndElement "member"

    StartMemberElement "datafile info"
    sql="col tablespace_name for a15
col file_name for a50
select * from (
select tablespace_name, file_name, bytes/1024/1024 as Used_Size_M, maxbytes/1024/1024 as Max_Size_M, autoextensible from dba_data_files
union all
select tablespace_name, file_name, bytes/1024/1024 as Used_Size_M, maxbytes/1024/1024 as Max_Size_M, autoextensible from dba_temp_files
);"
    sqlcmd2
    EndElement "member"

    StartMemberElement "dbuser info"
    sql="col default_tablespace form a25
    col temporary_tablespace form a10
    col username form a20
    col account_status form a18
    select username,default_tablespace,temporary_tablespace,account_status,expiry_date from dba_users where account_status not like 'EXPIRED _ LOCKED';"
    sqlcmd2 2>&1|sed -r 's/<|&/_/g'
    EndElement "member"

    StartMemberElement "fail jobs"
    sql="col what for a30
    select job, next_date,next_sec,failures,what from dba_jobs where failures<>0;
    declare
      a_cnt number;
    begin
      select count(*) into a_cnt from dba_jobs where failures<>0;
      if a_cnt = 0 then
        dbms_output.put_line('no records');
      end if;
    end;
    /"
    sqlcmd2 2>&1|sed -r 's/<|&/_/g'
    EndElement "member"

    StartMemberElement "invalid indexes"
    sql="COL index_name form a30
    Col owner form a10
    Col table_name form a20
    Col tablespace_name form a20
    select index_name,owner,table_name,tablespace_name from dba_indexes where owner not in ('SYS','SYSTEM') and status != 'VALID';
    declare
      b_cnt number;
    begin
      select count(*) into b_cnt from dba_indexes where owner not in ('SYS','SYSTEM') and status != 'VALID';
      if b_cnt = 0 then
        dbms_output.put_line('no records');
      end if;
    end;
    /"
    sqlcmd2 2>&1|sed -r 's/<|&/_/g'
    EndElement "member"

    StartMemberElement "failure objects"
    sql="COL OBJECT_NAME FORM A30
    select object_name, object_type, owner,status from dba_objects where status !='VALID' and owner not in ('SYS','SYSTEM') and object_type in ('TRIGGER','VIEW','PROCEDURE','FUNCTION');
    declare
      c_cnt number;
    begin
      select count(*) into c_cnt from dba_objects where status !='VALID' and owner not in ('SYS','SYSTEM') and object_type in ('TRIGGER','VIEW','PROCEDURE','FUNCTION');
      if c_cnt = 0 then
        dbms_output.put_line('no records');
      end if;
    end;
    /"
    sqlcmd2 2>&1|sed -r 's/<|&/_/g'
    EndElement "member"

    StartMemberElement "deadlocks"
    sql="SELECT l.session_id sid,
            s.serial#,
            s.blocking_session,
            l.locked_mode,
            l.oracle_username,
            s.user#,
            l.os_user_name,
            s.machine,
            s.terminal,
            a.action,
            a.sql_text
       FROM v\\\$sqlarea a, v\\\$session s, v\\\$locked_object l
      WHERE l.session_id = s.sid
        AND s.prev_sql_addr = a.address
      ORDER BY sid, s.serial#;
    declare
      d_cnt number;
    begin
      select count(*) into d_cnt from v\\\$sqlarea a, v\\\$session s, v\\\$locked_object l WHERE l.session_id = s.sid AND s.prev_sql_addr = a.address;
      if d_cnt = 0 then
        dbms_output.put_line('no records');
      end if;
    end;
    /"
    sqlcmd2 2>&1|sed -r 's/<|&/_/g'
    EndElement "member"

    StartMemberElement "database backup"
    get_cron() {
        local user=$1
        local cron_content=""
        if [ -f "/var/spool/cron/$user" ]; then
            cron_content=$(cat "/var/spool/cron/$user" 2>/dev/null)
        elif [ -f "/var/spool/cron/crontabs/$user" ]; then
            cron_content=$(cat "/var/spool/cron/crontabs/$user" 2>/dev/null)
        fi
        if [ -z "$cron_content" ]; then
            if [ "$user" = "root" ]; then
                cron_content=$(crontab -l 2>/dev/null)
            else
                cron_content=$(su - "$user" -c "crontab -l 2>/dev/null")
            fi
        fi
        echo "$cron_content" | grep -v '^#' | sed '/^$/d'
    }

    root_cron=$(get_cron "root")
    oracle_cron=$(get_cron "$ORACLE_USER")

    if [ -n "$root_cron" ]; then
        echo "root:"
        echo "$root_cron" | sed -r 's/<|&//g'
    fi
    if [ -n "$oracle_cron" ]; then
        echo "$ORACLE_USER:"
        echo "$oracle_cron" | sed -r 's/<|&//g'
    fi
    if [ -z "$root_cron" -a -z "$oracle_cron" ]; then
        echo "没有设置定时任务"
    fi
    EndElement "member"

    EndElement "section"

    EndElement "systemchecklog"
}


################################################################################
COLLECT_ONLINE=0
CheckRoot
OsCheck
GetProjectNameAndAssetId
GetOracleUser
CommandCheck
sqlpluscmd_check_fun
echo "$(InsertNode)${BROWN}Inspecting...${NORMAL}"
GenerateXml > oracle_check_`date +%Y%m%d%H%M%S`.xml
if [[ $? -ne 0 ]]; then
    echo "$(InsertNode)${RED}Data collection failed, no XML file was generated.${NORMAL}"
fi
if [ $COLLECT_ONLINE -eq 0 ];then
    mkdir $ASSETID 2> /dev/null
    mv oracle_check_*.xml $ASSETID
    echo "$(InsertNode)${LIGHTGREEN}Data collection is complete, please upload the XML file manually.${NORMAL}"
fi
