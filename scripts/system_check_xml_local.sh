#!/bin/bash
LANG=C
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
source /etc/profile

YELLOW="$(printf '\033[1;33m')"
LIGHTGREEN="$(printf '\033[0;32m')"
GREEN="$(printf '\033[1;32m')"
RED="$(printf '\033[1;31m')"
CYAN="$(printf '\033[0;36m')"
LIGHTBLUE="$(printf '\033[0;94m')"
BROWN="$(printf '\033[0;33m')"
NORMAL="$(printf '\033[0m')"


# 插入节点标记
InsertNode(){
    echo " ${YELLOW}*${NORMAL} ${RED}[$(date "+%Y-%m-%d %H:%M:%S")]${NORMAL}${CYAN}[$$]${NORMAL} "
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

# 命令检查信息
CommandCheck(){
    if which python >/dev/null 2>&1;then
        python=python
    elif which python3 >/dev/null 2>&1;then
        python=python3
    else
        echo "${RED}Python / python3 command not found.${NORMAL}"
        exit 2
    fi
    which ip >/dev/null 2>&1
    if [ $? -ne 0 ];then echo "${RED}ip command not found.${NORMAL}";exit 2;fi
    which sha256sum >/dev/null 2>&1
    if [ $? -ne 0 ];then echo "${RED}sha256sum command not found.${NORMAL}";exit 2;fi
    #which dmidecode >/dev/null 2>&1
    #if [ $? -ne 0 ];then echo "${RED}dmidecode command not found.${NORMAL}";exit 2;fi
    which swapon >/dev/null 2>&1
    if [ $? -ne 0 ];then echo "${RED}swapon command not found.${NORMAL}";exit 2;fi
    which wc >/dev/null 2>&1
    if [ $? -ne 0 ];then echo "${RED}wc command not found.${NORMAL}";exit 2;fi
}

# OS检查信息
OsCheck(){
    GetDistroInfo
    if echo ${DISTRO_NAME} | grep -Eqvi "Anolis|CentOS|Ubuntu|Red|Oracle"; then
        echo "${RED}Error: This script is only applicable to Anolis/redhat/centos/ubuntu/Oracle Linux!${NORMAL}"
        exit 2
    fi
    DistroName="$DISTRO_NAME"
}

# root检查信息
CheckRoot(){
    if [ $(id -u) != "0" ]; then
        echo "${RED}Error: You must use root to run this script. Please switch to root!${NORMAL}"
        exit 2
    fi
}

# 获取学校名称和资产ID信息
GetSchoolNameAndAssetId(){
    if [ ! -s "/etc/assetname" ]; then
        echo "${RED}Please fill in the asset information to /etc/assetname first.${NORMAL}"
        echo "${RED}Examples：school name-system name-192.168.0.1${NORMAL}"
        exit 2
    else
        SCHOOLNAME=$(awk -F "-" '{print $1}' /etc/assetname)
        ASSETID=$(cat /etc/assetname | sha256sum | awk '{print $1}')
        echo "$(InsertNode)${GREEN}SCHOOL:            ${SCHOOLNAME}${NORMAL}"
        echo "$(InsertNode)${GREEN}ASSET ID:          ${ASSETID}${NORMAL}"
    fi
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

    StartElement "school"
    awk -F- '{print($1);}' /etc/assetname
    EndElement "school"

    StartElement "application"
    awk -F- '{print($2);}' /etc/assetname
    EndElement "application"

    StartElement "assetid"
    cat /etc/assetname|sha256sum|awk '{print($1);}'
    EndElement "assetid"


    # 2 OS信息
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
    EndElement "member"

    StartMemberElement "model"
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
        "Anolis"|"CentOS"|"CentOS Linux"|"Red Hat Enterprise Linux Server")
            if which systemctl > /dev/null 2>&1;then
                if systemctl status firewalld > /dev/null 2>&1;then echo "enable";else echo "disable";fi
            else
                if service iptables status > /dev/null 2>&1;then echo "enable";else echo "disable";fi
            fi
            ;;
        "Ubuntu")
            if ufw status | grep -q inactive;then echo "disable";else echo "enable";fi
            ;;
    esac
    EndElement "member"

    StartMemberElement "selinux status"
    if echo ${DistroName} | grep -qE "CentOS|Red|Anolis";then getenforce;else echo "---";fi
    EndElement "member"

    StartMemberElement "system installation time"
    SIT=$(find /var/log/ -name "anaconda.log" -exec ls -l --full-time '{}' \;|awk '{print($6,$7);}'|awk -F. '{print($1);}')
    if [[ ${SIT} == "" ]]; then
        SIT=$(find /root/ -name "install.log.syslog" -exec ls -l --full-time '{}' \;|awk '{print($6,$7);}'|awk -F. '{print($1);}')
    fi
    if [[ ${SIT} == "" ]]; then
        SIT=$(find /root/ -name "anaconda-ks.cfg" -exec ls -l --full-time '{}' \;|awk '{print($6,$7);}'|awk -F. '{print($1);}')
    fi
    if [[ ${SIT} == "" ]]; then
        SIT=$(find /var/log/ -name  "installer" -exec ls -ld --full-time '{}' \;|awk '{print($6,$7);}'|awk -F. '{print($1);}')
    fi
    echo ${SIT}
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

    StartMemberElement "main service"
    if which netstat  > /dev/null 2>&1;then
        echo ""`netstat -lntp|awk -F/ '{if(NR>2){print($2)}}'|awk -F"[: ]" '{print($1)}'|grep -v '^master'|sort -u| awk 'BEGIN{ORS=" | "}{print $0}' | sed 's/...$//'`""
    elif which ss  > /dev/null 2>&1;then
        echo ""`ss -lntp | awk -F [\"] '{if(NR>2){print($2)}}' |grep -v '^master'|sort -u| awk 'BEGIN{ORS=" | "}{print $0}' | sed 's/...$//'`""
    fi
    EndElement "member"

    EndElement "section"


    # 4 内存信息
    StartSectionElement "Memory Info"
    
    StartMemberElement "memory total"
    awk '/MemTotal/{t=$2}END{printf("%.2fGB",t/1048576)}' /proc/meminfo
    EndElement "member"

    StartMemberElement "system memory used"
    awk '/MemTotal/{t=$2}/MemFree/{f=$2}END{printf("%.2f%%", (t-f)/t*100)}' /proc/meminfo
    EndElement "member"

    StartMemberElement "app memory used"
    awk '
    /MemTotal/{total=$2}
    /MemFree/{free=$2}
    /Buffers/{buf=$2}
    /^Cached/{cache=$2}
    /SReclaimable/{sr=$2}
    /Shmem/{sh=$2}
    /MemAvailable/{avail=$2}
    END{
        if(avail>0){ma=avail}else{ma=free+buf+cache+sr-sh;if(ma<0)ma=0}
        rate=(total-ma)/total*100
        printf("%.2f%%",rate)
    }' /proc/meminfo
    EndElement "member"

    StartMemberElement "Swap Info"
    
    # 修复原swap判断bug版本
    if [ $(swapon -s | grep -v Filename | wc -l) -eq 0 ];then echo no ;else echo yes;fi
    EndElement "member"
    
    EndElement "section"

    # 5 CPU信息
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

    # 6 磁盘/IO信息
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
	df -hP | grep "^/" | grep -Ev "/dev/loop" | grep -v "/boot" |awk '/%/{print($NF,$(NF-4),$(NF-3),"Use%:"$(NF-1));}' | sort -t ":" -nrk2;df -hP | grep "/boot" |awk '/%/{print($NF,$(NF-4),$(NF-3),"Use%:"$(NF-1));}'
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


    # 8 COURSE信息
    StartSectionElement "Course Info"

    StartMemberElement "course status"
    top -bin 1|awk '{if(/Tasks/){print(substr($0,7));}}'
    EndElement "member"

    StartMemberElement "self-starting services"
    if which systemctl > /dev/null  2>&1;then
        if which chkconfig > /dev/null  2>&1;then
            echo ""`ls /etc/systemd/system/multi-user.target.wants|grep -e ""|awk -F. '{print($1);}' && chkconfig --list 2>/dev/null|grep -Ee '3:on|5:on'|awk '{print($1);}'`""
        else
            echo ""`ls /etc/systemd/system/multi-user.target.wants|grep -e ""|awk -F. '{print($1);}'`""
        fi
    elif which chkconfig > /dev/null  2>&1;then
        echo ""`chkconfig --list 2>/dev/null|grep -Ee '3:on|5:on'|awk '{print($1);}'`""
    fi
    EndElement "member"

    StartMemberElement "cpu used rank"
    ps aux|head -1;ps aux|grep -v PID|sort -rn -k +3|head -5|sed -r 's/<|&//g'
    EndElement "member"

    StartMemberElement "memory used rank"
    ps aux|head -1;ps aux|grep -v PID|sort -rn -k +4|head -5|sed -r 's/<|&//g'
    EndElement "member"

    EndElement "section"


    # 9 日志信息
    StartSectionElement "Log Info"

    StartMemberElement "log size rank"
    du -sh /var/log/* 2>/dev/null|grep -Ee '\wM|\wG'|sort -nr
    EndElement "member"

    EndElement "section"


    # 10 安全检查信息
    StartSectionElement "Security Check"

    StartMemberElement "sshd check"

    StartNodeElement "port"
    sshd_pid=`ps -ef | grep sbin/sshd |grep -v grep | awk '{print $2}'`
    sshd_dir=`ls -l /proc/$sshd_pid | grep sbin/sshd |awk '{print $NF}' | awk -F '/sbin' '{print $1}'`
    if [ $sshd_dir = /usr ];then
        sshd_etc=/etc
    else
        sshd_etc=$sshd_dir/etc
        find $sshd_etc -name sshd_config &> /dev/null
        if [ $? -ne 0 ];then
            sshd_etc=/etc
        fi
    fi
    sshd_config=`find $sshd_etc -name sshd_config | grep etc`
    awk '{if(/^#Port /){PORT=$2;}else if(/^Port /){PORT=$2}} END{print(PORT);}' $sshd_config 2> /dev/null
    EndElement "node"

    StartNodeElement "permit root login"
	if test -z "$(cat $sshd_config|grep "^Per")";then
	    if test "$($sshd_dir/bin/ssh -V 2>&1| awk -F[_.] '{print $2}')" -eq 5;then
		    echo yes
		else
		    echo no
		fi
	else
		awk '/^PermitRootLogin /{if($2 == "yes" || $2 == "no"){print($2);}}' $sshd_config 2> /dev/null
	fi
    EndElement "node"

    StartNodeElement "dns analysis"
    awk '/^UseDNS /{print($2);}' $sshd_config 2> /dev/null
    EndElement "node"

    StartNodeElement "version(include SSL)"
    echo `$sshd_dir/bin/ssh -V 2>&1`
    EndElement "node"

    EndElement "member"

    StartMemberElement "login check"

    StartNodeElement "login timeout"
    if [[ ${TMOUT} == "" ]];then echo "---";else echo ${TMOUT};fi
    EndElement "node"

    StartNodeElement "login times rank"
    last -a|awk '/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/{print($NF);}'|sort|uniq -c|sort -nr -k +1
    EndElement "node"

    StartNodeElement "login on count"
    w -h|wc -l
    EndElement "node"

    StartNodeElement "login on status"
    w
    EndElement "node"

    EndElement "member"

    StartMemberElement "other check"

    StartNodeElement "system key files status"
    ls -ldt --full-time /etc/passwd /etc/shadow /etc/group /etc/gshadow /etc/services /etc/rc[0-9].d|awk '{print($6,$7,$9);}'
    EndElement "node"

    StartNodeElement "timed task"
    crontab -l 2>&1|sed -r 's/<|&//g'
    EndElement "node"

    StartNodeElement "default profile for adding user"
    cat /etc/default/useradd
    grep -Ee "^PASS_MAX_DAYS|^PASS_MIN_DAYS|^PASS_MIN_LEN|^PASS_WARN_AGE|^UMASK" /etc/login.defs
    ls -alt --full-time /etc/skel|awk '{print($1,$3,$4,$6,$7,$9);}'|grep -Eve "^d|^total"
    EndElement "node"

    StartNodeElement "remote access control files"
    tail -n 5 /etc/hosts.* 2> /dev/null|sed -r 's/<|&//g'
    EndElement "node"

    StartNodeElement "local hosts file"
    cat /etc/hosts
    EndElement "node"

    StartNodeElement "auditd status"
    if which auditd > /dev/null 2>&1;then
        if which systemctl > /dev/null 2>&1;then
            if systemctl status auditd > /dev/null 2>&1;then echo "enable";else echo "disable";fi
        else
            if service auditd status > /dev/null 2>&1;then echo "enable";else echo "disable";fi
        fi
    else
        echo "---"
    fi
    EndElement "node"

    EndElement "member"

    EndElement "section"


    StartSectionElement "From"

    StartMemberElement "java home"
    if [[ ${JAVA_HOME} == "" ]];then echo "---";else echo ${JAVA_HOME};fi
    EndElement "member"

    StartMemberElement "env"
    env | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g'
    EndElement "member"

    StartMemberElement "iptables config"
    iptables -L -n --line-number|sed -r 's/<|&//g'
    EndElement "member"

    EndElement "section"

    EndElement "systemchecklog"
}


###################################################################################################################
COLLECT_ONLINE=0
CommandCheck
OsCheck
CheckRoot
GetSchoolNameAndAssetId
echo "$(InsertNode)${BROWN}Inspecting...${NORMAL}"
GenerateXml > system_check_`date +%Y%m%d%H%M%S`.xml
if [[ $? -ne 0 ]]; then
    echo "$(InsertNode)${RED}Data collection failed, no XML file was generated.${NORMAL}"
else
    echo "$(InsertNode)Data collection succeeded."
fi
if [ $COLLECT_ONLINE -eq 0 ];then
    mkdir $ASSETID 2> /dev/null
    mv system_check_*.xml $ASSETID
    echo "$(InsertNode)${LIGHTGREEN}Data collection is complete, please upload the XML file manually.${NORMAL}"
fi
