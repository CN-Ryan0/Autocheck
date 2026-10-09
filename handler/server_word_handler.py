# -*- coding: utf-8 -*-
"""
服务器巡检报告生成模块
包含检测器、结果与建议处理器、报告生成器。

@author: Ryan和他的小伙伴们
@date: 2026-10-09
@version: 2.1
"""

import os
import re
import time
from os import path as op
from collections import defaultdict
from docxtpl import DocxTemplate
from xml_handler import XmlParser


class Detector:
    """检索 XML 日志文件中的指标，并与阈值比较，返回状态码"""

    STATE_OK = 0
    STATE_WARNING = 1
    STATE_CRITICAL = 2
    STATE_UNKNOWN = 3

    def __init__(self, **kwargs):
        if kwargs:
            self.limit = kwargs
        else:
            self.limit = {
                'osversion': ('lt', 6, '-'),
                'cpuprocessor': ('lt', 4, 2),
                'mem': ('lt', 4, 3),
                'hostname': ('in', 'localhost.localdomain', '-'),
                'mainservice': ('notin', ['java', 'jsvc', 'ora', 'nginx', 'dockerd'], '-'),
                'iptablesstatus': ('eq', '关闭', '-'),
                'sysnowtime': ('lt', time.mktime(time.localtime()) - 3*60*60,
                               time.mktime(time.localtime()) - 6*60*60),
                'sysuptime': ('lt', 6, 3),
                'cpuused': ('lt', 50, 35),
                'appmemused': ('gt', 70, 80),
                'diskused': ('gt', 85, 92),
                'inodesused': ('gt', 80, 90),
                'sysload': ('gt', 2, 4),
                'link': ('gt', 500, 1000),
                'course-t': ('gt', 500, 1000),
                'course-z': ('gt', 0, 1),
                #'sshdport': ('eq', 22, '-'),
                #'permitrootlogin': ('eq', 'yes', '-'),
                #'timeout': ('inverse', ['---', '未设置'], '-'),
                'timedtask': ('inverse', ['wget'], '-'),
                #'racf': ('notin', [':allow', ':ALLOW', ':deny', ':DENY',
                                   #': allow', ': ALLOW', ': deny', ': DENY'], '-'),
            }

    def _special_limittype_handler(self, limittype, value):
        if limittype in ('mem', 'sysuptime', 'appmemused'):
            return re.sub(r'GB|天|%', '', value)
        elif limittype == 'sysnowtime':
            return time.mktime(time.strptime(value, '%Y-%m-%d %H:%M:%S'))
        elif limittype == 'sysload':
            parts = value.split()
            return parts[2] if len(parts) >= 3 else value
        elif limittype in ('diskused', 'inodesused'):
            lines = value.split('\n')
            if lines:
                match = re.search(r'(\d+)%', lines[0])
                if match:
                    return match.group(1)
            return '0'
        elif limittype == 'cpuused':
            match = re.search(r'(\d+\.?\d*)\s*id', value)
            if match:
                return match.group(1)
            return '0'
        elif limittype == 'link':
            numbers = re.findall(r'\d+', value.replace('|', ' '))
            return str(max(map(int, numbers))) if numbers else '0'
        elif limittype == 'course-t':
            match = re.search(r'(\d+)\s*total', value)
            return match.group(1) if match else '0'
        elif limittype == 'course-z':
            match = re.search(r'(\d+)\s*zombie', value)
            return match.group(1) if match else '0'
        else:
            return value

    def probe_number(self, limittype, value):
        try:
            processed = self._special_limittype_handler(limittype, value)
            val = float(processed)
            op_type, warn_val, crit_val = self.limit[limittype]

            if op_type == 'gt':
                if crit_val != '-' and val > float(crit_val):
                    return self.STATE_CRITICAL
                if val > float(warn_val):
                    return self.STATE_WARNING
            elif op_type == 'lt':
                if crit_val != '-' and val < float(crit_val):
                    return self.STATE_CRITICAL
                if val < float(warn_val):
                    return self.STATE_WARNING
            elif op_type == 'eq':
                if crit_val != '-' and val == float(crit_val):
                    return self.STATE_CRITICAL
                if val == float(warn_val):
                    return self.STATE_WARNING
        except Exception:
            return self.STATE_UNKNOWN
        return self.STATE_OK

    def probe_str(self, limittype, value):
        try:
            op_type, warn_val, crit_val = self.limit[limittype]
            if op_type == 'eq':
                if crit_val != '-' and value == crit_val:
                    return self.STATE_CRITICAL
                if value == warn_val:
                    return self.STATE_WARNING
            elif op_type == 'in':
                if crit_val != '-' and value in crit_val:
                    return self.STATE_CRITICAL
                if value in warn_val:
                    return self.STATE_WARNING
            elif op_type == 'inverse':
                if crit_val != '-' and any(kw in value for kw in crit_val):
                    return self.STATE_CRITICAL
                if any(kw in value for kw in warn_val):
                    return self.STATE_WARNING
            elif op_type == 'notin':
                if crit_val != '-' and not any(kw in value for kw in crit_val):
                    return self.STATE_CRITICAL
                if not any(kw in value for kw in warn_val):
                    return self.STATE_WARNING
        except Exception:
            return self.STATE_UNKNOWN
        return self.STATE_OK

    def probe(self, limittype, value):
        numeric_types = ('osversion', 'cpuprocessor', 'mem', 'sysnowtime',
                         'sysuptime', 'sysload', 'link', 'course-t', 'course-z',
                         'cpuused', 'appmemused', 'diskused', 'inodesused') # sshdport
        string_types = ('hostname', 'mainservice', 'iptablesstatus','timedtask') # permitrootlogin, timeout, racf

        if limittype in numeric_types:
            return self.probe_number(limittype, value)
        elif limittype in string_types:
            return self.probe_str(limittype, value)
        else:
            return self.STATE_UNKNOWN


class ResultAndSuggest:
    """服务器资源评估结果及对应的处理建议"""

    def __init__(self):
        self.resultset = {
            'mem': {1: '内存资源分配过剩', 2: '严重的内存资源分配过剩'},
            'hostname': {1: '主机名为默认的localhost'},
            'sysuptime': {1: '系统稳定性较低', 2: '系统稳定性很低'},
            'sysnowtime': {1: '服务器时间未同步', 2: '服务器时间严重不同步'},
            'sysload': {1: '系统负载较高', 2: '系统负载很高'},
            'timedtask': {1: '存在异常的定时任务'},
            'mainservice': {1: '服务器没有运行有效的服务'},
            'appmemused': {1: '内存利用率较高', 2: '内存利用率很高'},
            'cpuused': {1: 'CPU利用率较高', 2: 'CPU利用率很高'},
            'diskused': {1: '磁盘资源不足', 2: '磁盘资源严重不足'},
            'link': {1: 'TCP链接数较高', 2: 'TCP链接数很高'},
            'course': {1: '服务器运行的进程较多', 2: '服务器运行的进程很多'},
            'iptablesstatus': {1: 'iptable防火墙未开启'},
            #'sshdport': {1: 'SSHD服务使用默认端口'},
            #'permitrootlogin': {1: 'SSHD服务允许root账户登录'},
            #'timeout': {1: '服务器终端未设置超时参数'},
            #'racf': {1: '服务器未设置访问控制规则'},
        }

        # 注释不需要的建议
        self.suggestset = {
            'mem': {
                1: ["建议合理分配内存资源。",
                    "如果该服务器确实需要这么多内存资源，建议调整程序参数以充分利用内存资源。"],
                2: ["强烈建议合理分配内存资源。",
                    "如果该服务器确实需要这么多内存资源，强烈建议调整程序参数以充分利用内存资源。"]
            },
            'hostname': {
                1: ["服务器应具有自己的主机名，用于标识服务器的用途及其它相关信息。",
                    "主机名还可以用于实现传输层的动态互联，不必受到IP的干扰（需要修改hosts文件）。"]
            },
            'sysuptime': {
                1: ["服务器稳定性较低，服务器应保持连续性的工作状态。",
                    "服务器应具备24/7的工作能力，但服务器存在这样的问题时，建议多关注。"],
                2: ["服务器稳定性很低，服务器应保持连续性的工作状态。",
                    "服务器应具备24/7的工作能力，但服务器存在这样的问题时，建议多关注。"]
            },
            'sysnowtime': {
                1: ["实时同步的时间对大部分程序来说是很重要的。",
                    "服务器时间可以用来描述一个文件/一条数据等的创建、修改、更新情况，这些属性应具备准确性。"],
                2: ["实时同步的时间对大部分程序来说是很重要的。",
                    "服务器时间可以用来描述一个文件/一条数据等的创建、修改、更新情况，这些属性应具备准确性。"]
            },
            'sysload': {
                1: ["此项表示系统的整体负载，当过高时需要注意。",
                    "15分钟的负载平均值不应该超过CPU的核心数，建议检查是机器的哪一部分出现故障。",
                    "负载值存在浮动是正常的。"],
                2: ["此项表示系统的整体负载，当过高时需要注意。",
                    "15分钟的负载平均值不应该超过CPU的核心数，建议检查是机器的哪一部分出现故障。",
                    "负载值存在浮动是正常的。"]
            },
            'timedtask': {
                1: ["定时任务是系统的一个调度服务，具有定时执行程序等的功能。",
                    "当发现定时任务存在非法条目时，说明该系统已被非法人员入侵。",
                    "建议保留系统状态，排查存在漏洞的地方。"]
            },
            'mainservice': {
                1: ["如果不再使用该业务系统，建议关闭机器以保障系统在网络上的安全和对硬件及外围资源的浪费。",
                    "服务器应该运行有效的服务，建议确认下是否停止了该业务。"]
            },
            'appmemused': {
                1: ["当前的内存使用率较高，建议持续监控其增长趋势，及时采取措施。",
                    "内存资源应控制一定的剩余量，以保证能持续分配给程序使用。",
                    "可以适当的增加内存资源或减少服务器运行的程序。"],
                2: ["当前的内存使用率很高，建议持续监控其增长趋势，及时采取措施。",
                    "内存资源应控制一定的剩余量，以保证能持续分配给程序使用。",
                    "可以适当的增加内存资源或减少服务器运行的程序。"]
            },
            'cpuused': {
                1: ["当前CPU使用率较高，建议持续监控其增长趋势，及时采取措施。",
                    "CPU使用率应保持在一定的范围，长期过高时可能是出现了问题，建议排查。"],
                2: ["当前CPU使用率很高，建议持续监控其增长趋势，及时采取措施。",
                    "CPU使用率应保持在一定的范围，长期过高时可能是出现了问题，建议排查。"]
            },
            'diskused': {
                1: ["磁盘是数据存放的地方，需要保持一定的容量，具体容量根据业务的不同及数据增长趋势调节。",
                    "如果出现了该现象，说明磁盘空间不足，建议扩充或删除不重要的历史数据进行缓解。"],
                2: ["磁盘是数据存放的地方，需要保持一定的容量，具体容量根据业务的不同及数据增长趋势调节。",
                    "如果出现了该现象，说明磁盘空间严重不足，建议立刻扩充或删除不重要的历史数据进行缓解，否则将影响业务正常运行。"]
            },
            'link': {
                1: ["链接数长期过高说明业务用户量较大，建议时刻关注服务器状态指标。",
                    "链接数过大也可能是非法的拒绝服务攻击，建议进行排查及做好相应的措施。"],
                2: ["链接数长期过高说明业务用户量较大，建议时刻关注服务器状态指标。",
                    "链接数过大也可能是非法的拒绝服务攻击，建议进行排查及做好相应的措施。"]
            },
            'course': {
                1: ["服务器运行的进程数不应超过相应的量，具体根据服务器性能来判断。",
                    "当出现该现象时，说明服务器在高负荷下工作。",
                    "此事件一般出现在某服务异常时发生，如sendmail服务，通常是由硬件异常导致的。"],
                2: ["服务器运行的进程数远超合理范围，系统负荷极高。",
                    "建议立即检查异常进程（如挖矿、僵尸进程等），并排查硬件或服务故障。",
                    "建议限制最大进程数，并启用进程审计。"]
            },
            'iptablesstatus': {
                1: ["iptables是Redhat系列操作系统自带的软件防火墙，可以设置控制访问规则。",
                    "防火墙filter表应该只暴露必要的服务及管理端口，防止人员扫描、收集信息。"]
            },
            #'sshdport': {
            #    1: ["SSHD服务是连接服务器的主要通道，建议修改默认端口。"]
            #},
            #'permitrootlogin': {
            #    1: ["服务器使用root超级账户登录是危险的，建议统一使用普通账户进行权集分治。",
            #        "当然这是很普遍的现象，这里只是以建议的角度看待这个问题，并非强制性的要求。"]
            #},
            #'timeout': {
            #    1: ["为了连接服务器的安全性考虑，建议设置终端超时参数。",
            #        "设置该值可避免人为长时间的连接服务器而不进行任何操作。"]
            #},
            #'racf': {
            #    1: ["访问控制文件具有限制访问必要的对象及服务的功能，可以对一些需要安全性比较高服务进行访问限制。",
            #        "在普遍的应用中对SSHD服务的访问限制比较多，毕竟要把安全放在第一位。"]
            #},
        }

    def result(self, limittype, value):
        return self.resultset.get(limittype, {}).get(value, '未知结果')

    def suggest(self, limittype, value):
        suggestions = self.suggestset.get(limittype, {}).get(value, ['暂无建议'])
        return "\n".join([f"{i+1}. {text}" for i, text in enumerate(suggestions)])


class ServerWordHandler:
    """服务器巡检报告生成器"""

    def __init__(self, filedict):
        self.dc_obj = Detector()
        self.rs_obj = ResultAndSuggest()
        if isinstance(filedict, dict):
            self.filedict = filedict
        else:
            raise TypeError("filedict 必须是字典类型")

    def _process_result_and_suggest(self, value, limittype, appname, kwargs):
        if value is None:
            value = "无法获取"
            state = self.dc_obj.STATE_UNKNOWN
        else:
            state = self.dc_obj.probe(limittype, value)

        force_ok_types = ('hostname') # sshdport, timeout
        if limittype in force_ok_types:
            if state in (self.dc_obj.STATE_WARNING, self.dc_obj.STATE_CRITICAL):
                if limittype in ('mem', 'hostname'):
                    category = 'assets'
                elif limittype in ('sysuptime', 'sysload', 'timedtask', 'mainservice',
                                   'appmemused', 'cpuused', 'diskused', 'link', 'course'):
                    category = 'osandperformance'
                elif limittype in ('iptablesstatus', 'timedtask'): # sshdport, permitrootlogin, timeout, racf
                    category = 'security'
                else:
                    category = None

                if category:
                    result_text = self.rs_obj.result(limittype, state) + f"（{appname}）"
                    kwargs['suggest'][category][result_text] = self.rs_obj.suggest(limittype, state)
            state = self.dc_obj.STATE_OK
        else:
            if state in (self.dc_obj.STATE_WARNING, self.dc_obj.STATE_CRITICAL):
                if limittype in ('mem', 'hostname'):
                    category = 'assets'
                elif limittype in ('sysuptime', 'sysload', 'timedtask', 'mainservice',
                                   'appmemused', 'cpuused', 'diskused', 'link', 'course'):
                    category = 'osandperformance'
                elif limittype in ('iptablesstatus', 'timedtask'): # sshdport, permitrootlogin, timeout, racf
                    category = 'security'
                else:
                    category = None

                if category:
                    result_text = self.rs_obj.result(limittype, state) + f"（{appname}）"
                    kwargs['check_result'][category].append(result_text)
                    kwargs['suggest'][category][result_text] = self.rs_obj.suggest(limittype, state)

        return [value, state]

    def parsexfl(self, projectname, filelist, **kwargs):
        kwargs['projectname'] = projectname
        checktimelist = []
        for file in filelist:
            xp = XmlParser(file)
            t = xp.get_member('system now time')
            if t:
                checktimelist.append(t)
        kwargs['checkdate'] = max(checktimelist)[:10] if checktimelist else "未知日期"
        kwargs['checkusername'] = kwargs.get('checkusername', '巡检人')

        kwargs['base_info'] = []
        kwargs['system_check'] = []
        kwargs['performance_check'] = []
        kwargs['security_check'] = []
        kwargs['check_result'] = {'assets': [], 'osandperformance': [], 'security': []}
        kwargs['suggest'] = {'assets': {}, 'osandperformance': {}, 'security': {}}

        for file in filelist:
            xp_obj = XmlParser(file)
            try:
                xp_obj.root
            except Exception as e:
                print(f" * [错误] {e}  -->  {file}")
                continue

            appname = xp_obj.get_application or "未知应用"

            cpu = (xp_obj.get_member('cpu processor') or "") + "线程" + (xp_obj.get_member('cpu model') or "")
            mem = xp_obj.get_member('memory total') or "未知"
            disk = xp_obj.get_member('disk') or "未知"
            osversion = (xp_obj.get_member('os type') or "") + " " + (xp_obj.get_member('os version') or "")
            arch = xp_obj.get_member('architecture') or "未知"
            ipaddr = xp_obj.get_member('ip address') or "未知"
            hostname_raw = xp_obj.get_member('hostname')
            hostname_processed = self._process_result_and_suggest(hostname_raw, 'hostname', appname, kwargs)
            javahome = xp_obj.get_member('java home') or "未设置"

            kwargs['base_info'].append({
                'appname': appname,
                'cpu': cpu,
                'mem': mem,
                'disk': disk,
                'osversion': osversion,
                'arch': arch,
                'ipaddr': ipaddr,
                'hostname': hostname_processed,
                'apppath': 'coding',
                'javahome': javahome,
            })

            swap = xp_obj.get_member('Swap Info') or "未知"
            kernelversion = xp_obj.get_member('kernel version') or "未知"
            sysuptime = xp_obj.get_member('system up time') or "未知"
            sysnowtime_raw = xp_obj.get_member('system now time')
            sysnowtime_processed = self._process_result_and_suggest(sysnowtime_raw, 'sysnowtime', appname, kwargs)
            sysload_raw = xp_obj.get_member('system load')
            sysload_processed = self._process_result_and_suggest(sysload_raw, 'sysload', appname, kwargs)
            hosts = xp_obj.get_node('other check', 'local hosts file') or "未配置"
            timedtask_raw = xp_obj.get_node('other check', 'timed task')
            timedtask_processed = self._process_result_and_suggest(timedtask_raw, 'timedtask', appname, kwargs)
            mainservice = xp_obj.get_member('main service') or "未运行"

            kwargs['system_check'].append({
                'appname': appname,
                'swap': swap,
                'kernelversion': kernelversion,
                'sysuptime': sysuptime,
                'sysnowtime': sysnowtime_processed,
                'sysload': sysload_processed,
                'hosts': hosts,
                'timedtask': timedtask_processed,
                'mainservice': mainservice,
            })

            memused_raw = xp_obj.get_member('app memory used')
            memused_processed = self._process_result_and_suggest(memused_raw, 'appmemused', appname, kwargs)
            cpuused_raw = xp_obj.get_member('cpu used')
            cpuused_processed = self._process_result_and_suggest(cpuused_raw, 'cpuused', appname, kwargs)
            diskused_raw = xp_obj.get_member('disk used human')
            diskused_processed = self._process_result_and_suggest(diskused_raw, 'diskused', appname, kwargs)
            link_raw = xp_obj.get_member('link status')
            link_processed = self._process_result_and_suggest(link_raw, 'link', appname, kwargs)
            course = xp_obj.get_member('course status') or "未知"

            kwargs['performance_check'].append({
                'appname': appname,
                'memused': memused_processed,
                'cpuused': cpuused_processed,
                'diskused': diskused_processed,
                'link': link_processed,
                'course': course,
            })

            iptables_raw = xp_obj.get_member('iptables status')
            iptables_processed = self._process_result_and_suggest(iptables_raw, 'iptablesstatus', appname, kwargs)
            sshdport_raw = xp_obj.get_node('sshd check', 'port')
            #sshdport_processed = self._process_result_and_suggest(sshdport_raw, 'sshdport', appname, kwargs)
            sshdport_processed = [sshdport_raw, self.dc_obj.STATE_OK]
            permit_root_raw = xp_obj.get_node('sshd check', 'permit root login')
            #permit_root_state = self.dc_obj.probe('permitrootlogin', permit_root_raw) if permit_root_raw else self.dc_obj.STATE_UNKNOWN
            #permit_root_display = [permit_root_raw or "未知", permit_root_state]
            permit_root_display = [permit_root_raw, self.dc_obj.STATE_OK]
            syskeyfiles = xp_obj.get_node('other check', 'system key files status') or "未获取"
            timeout_raw = xp_obj.get_node('login check', 'login timeout')
            timeout_processed = [timeout_raw, self.dc_obj.STATE_OK]
            racf_raw = xp_obj.get_node('other check', 'remote access control files')
            #racf_state = self.dc_obj.probe('racf', racf_raw) if racf_raw else self.dc_obj.STATE_UNKNOWN
            racf_display = [racf_raw, self.dc_obj.STATE_OK]
            auditd = xp_obj.get_node('other check', 'auditd status') or "未知"

            kwargs['security_check'].append({
                'appname': appname,
                'iptablesstatus': iptables_processed,
                'sshdport': sshdport_processed,
                'permitrootlogin': permit_root_display,
                'syskeyfiles': syskeyfiles,
                'timeout': timeout_processed,
                'racf': racf_display,
                'auditd': auditd,
            })

        def group_suggestions(suggest_dict):
            groups = defaultdict(lambda: {"servers": [], "advice_text": ""})
            for full_title, advice in suggest_dict.items():
                match = re.match(r'^(.*?)（(.*?)）$', full_title)
                if match:
                    issue = match.group(1)
                    app = match.group(2)
                else:
                    issue = full_title
                    app = "未知"
                groups[issue]["servers"].append(app)
                if not groups[issue]["advice_text"]:
                    groups[issue]["advice_text"] = advice + "\n"
            result = []
            for issue, data in groups.items():
                result.append({
                    "title": issue,
                    "servers": data["servers"],
                    "advice_text": data["advice_text"]
                })
            return result

        grouped_suggest = {
            'assets': group_suggestions(kwargs['suggest']['assets']),
            'osandperformance': group_suggestions(kwargs['suggest']['osandperformance']),
            'security': group_suggestions(kwargs['suggest']['security'])
        }
        kwargs['grouped_suggest'] = grouped_suggest

        return kwargs

    def output(self, outpath, username=None):
        outpath_abs = op.abspath(outpath)
        os.makedirs(outpath_abs, exist_ok=True)
        
        if username is None:
            username = input("请输入巡检人员姓名：").strip()
        if username == '':
            username = '巡检人'

        for sname, filelist in self.filedict.items():
            if not filelist:
                print(f"警告：服务器 {sname} 没有有效的 XML 文件，跳过报告生成")
                continue
            self.doc = DocxTemplate("server_template.docx")
            context = self.parsexfl(sname, filelist, checkusername=username)
            self.doc.render(context)
            checkdate = context.get('checkdate', '未知日期')
            if '-' in checkdate:
                year_month = checkdate.split('-', 2)[0] + '-' + checkdate.split('-', 2)[1]
            else:
                year_month = checkdate
            filename = f"{year_month}{sname}服务器巡检报告.doc"
            out_file = op.join(outpath_abs, filename)
            try:
                self.doc.save(out_file)
            except PermissionError as e:
                print(f"错误：无法保存文件 {out_file}，请确认文件未被其他程序打开，且当前用户有写入权限。")
                raise e
            print(f"已生成报告：{out_file}")
        return None
