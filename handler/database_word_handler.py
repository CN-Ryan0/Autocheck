# -*- coding: utf-8 -*-
"""
数据库巡检报告生成模块
包含图表生成器、结论和建议处理器、报告生成器。

@author: Ryan和他的小伙伴们
@date: 2026-06-12
@version: 2.0
"""

import os
import io
import re
from os import path as op
import matplotlib.pyplot as plt
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Inches
from xml_handler import XmlParser


class DatabaseWordHandler:
    """数据库巡检报告生成器"""

    def __init__(self, filedict):
        """
        初始化数据库巡检报告生成器
        :param filedict: 包含数据库配置信息的字典
        """
        if isinstance(filedict, dict):
            self.filedict = filedict
        else:
            raise TypeError("filedict 必须是字典类型")

    def _analyze_disk_usage(self, disk_used_human_str):
        """
        解析磁盘使用率数据
        """
        if not disk_used_human_str or '请使用最新的XML文件生成器' in disk_used_human_str:
            return "无法获取磁盘使用率数据。"
        lines = disk_used_human_str.strip().split('\n')
        warnings = []
        for line in lines:
            match = re.search(r'Use%:(\d+(?:\.\d+)?)%', line)
            if match:
                pct = float(match.group(1))
                mount = line.split()[0] if line.split() else 'unknown'
                if mount == '/':
                    mount = '根目录'
                if pct >= 90:
                    warnings.append(f"{mount} 使用率 {pct:.1f}%，严重偏高，请立即清理或扩容")
                elif pct >= 80:
                    warnings.append(f"{mount} 使用率 {pct:.1f}%，较高，建议关注并清理")
                elif pct >= 70:
                    warnings.append(f"{mount} 使用率 {pct:.1f}%，接近阈值，建议规划扩容")
        if warnings:
            return "；".join(warnings) + "。"
        else:
            return "磁盘使用率正常。"

    def _analyze_cpu_usage(self, cpu_usage_str):
        """
        解析CPU使用率数据
        """
        if not cpu_usage_str or '请使用最新的XML文件生成器' in cpu_usage_str:
            return "无法获取CPU数据。"
        match = re.search(r'(\d+\.?\d*)%?\s*id', cpu_usage_str)
        if match:
            idle = float(match.group(1))
            if idle < 20:
                return f"CPU 空闲率仅 {idle:.1f}%，负载过高，请检查高占用进程。"
            elif idle < 50:
                return f"CPU 空闲率 {idle:.1f}%，负载较高，建议排查。"
            else:
                return "CPU 负载正常。"
        return "无法解析 CPU 数据。"

    def _analyze_memory_usage(self, sys_used_pct_str):
        """
        解析内存使用率数据
        """
        if not sys_used_pct_str or '请使用最新的XML文件生成器' in sys_used_pct_str:
            return "无法获取内存数据。"
        pct = float(sys_used_pct_str.rstrip('%'))
        if pct >= 95:
            return f"内存使用率高达 {pct:.1f}%，严重不足，建议增加内存或优化应用。"
        elif pct >= 85:
            return f"内存使用率 {pct:.1f}%，较高，建议关注。"
        else:
            return "内存负载正常。"

    def _analyze_lsnrctl_status(self, lsnrctl_status_str):
        """
        解析数据库监听状态
        """
        if not lsnrctl_status_str or '请使用最新的XML文件生成器' in lsnrctl_status_str:
            return "无法获取数据库监听的配置信息。"
        if "READY" in lsnrctl_status_str:
            return "数据库监听配置正常。"
        else:
            return "数据库监听未开启，建议开启以确保数据库连接正常。"

    def _analyze_archive_mode(self, archive_mode_str):
        """
        解析归档模式
        """
        if not archive_mode_str or '请使用最新的XML文件生成器' in archive_mode_str:
            return "无法获取归档模式信息。"
        if "No Archive Mode" in archive_mode_str or "Disabled" in archive_mode_str:
            return "数据库未开启归档模式，建议开启以确保数据恢复能力。"
        else:
            return "归档模式已开启，配置正常。"

    def _analyze_tablespace_usage(self, tablespace_usage_str):
        """
        解析表空间信息、使用率
        """
        if not tablespace_usage_str or '请使用最新的XML文件生成器' in tablespace_usage_str:
            return "无法获取表空间信息。"

        lines = tablespace_usage_str.strip().split('\n')
        # 寻找表头行和数据行
        header_found = False
        data = []
        for line in lines:
            if 'TABLESPACE_NAME' in line:
                header_found = True
                continue
            if not header_found:
                continue
            # 跳过分隔线（如 ----）和空行
            if line.strip().startswith('---') or line.strip() == '':
                continue
            # 按空白分割，列顺序：TABLESPACE_NAME, FREE_SIZE_M, SIZE_M, USED_SIZE_M, MAX_SIZE_M, PERCENT_USED, PERCENT_MAX_USED
            parts = line.split()
            if len(parts) >= 7:
                ts_name = parts[0]
                # 将字符串转为浮点数
                total_m = float(parts[2])      # SIZE_M
                used_m = float(parts[3])       # USED_SIZE_M
                pct_used = float(parts[5])     # PERCENT_USED
                data.append((ts_name, used_m, total_m, pct_used))

        if not data:
            return "未检测到表空间信息，请检查数据库配置。"

        # 逐个分析并汇总
        details = []
        warnings = []
        critical_warnings = []   # 用于严重问题（≥90%）

        for ts, used, total, pct in data:
            if pct >= 90:
                msg = (f"{ts} 使用率 {pct:.1f}%")
                critical_warnings.append(msg)
            elif pct >= 80:
                msg = (f"{ts} 使用率 {pct:.1f}%")
                warnings.append(msg)
            elif pct >= 70:
                msg = (f"{ts} 使用率 {pct:.1f}%")
                warnings.append(msg)
            else:
                msg = f"{ts} 使用率 {pct:.1f}%"
                details.append(msg)

        # 严重问题优先展示
        result_parts = []
        if critical_warnings:
            result_parts.extend(critical_warnings)
        if warnings:
            result_parts.extend(warnings)
    
        if result_parts:
            # 拼接详细建议
            final_result = "；".join(result_parts) + "。请关注表空间使用情况。"
            return final_result
        else:
            return "表空间使用率正常。"

    def _analyze_temp_tablespace_usage(self, temptablespace_usage_str):
        """
        解析临时表空间信息、使用率
        """
        if not temptablespace_usage_str or '请使用最新的XML文件生成器' in temptablespace_usage_str:
             return "无法获取临时表空间信息。"

        lines = temptablespace_usage_str.strip().split('\n')
        # 寻找表头行和数据行
        header_found = False
        data = []
        for line in lines:
            if 'TABLESPACE_NAME' in line:
                header_found = True
                continue
            if not header_found:
                continue
            if line.strip().startswith('---') or line.strip() == '':
                continue
            # 按空白分割，列顺序：TABLESPACE_NAME, FREE_SIZE_M, SIZE_M, USED_SIZE_M, MAX_SIZE_M, PERCENT_USED, PERCENT_MAX_USED
            parts = line.split()
            if len(parts) >= 7:
                ts_name = parts[0]
                size_m = float(parts[2])       # SIZE_M
                used_m = float(parts[3])       # USED_SIZE_M
                pct_used = float(parts[5])     # PERCENT_USED
                data.append((ts_name, used_m, size_m, pct_used))

        if not data:
            return "未检测到临时表空间信息，请检查数据库配置。"

        # 逐个分析
        details = []
        warnings = []
        for ts, used, total, pct in data:
            if pct >= 80:
                msg = f"{ts} 使用率 {pct:.1f}%"
                warnings.append(msg)
            elif pct >= 70:
                msg = f"{ts} 使用率 {pct:.1f}%"
                warnings.append(msg)
            else:
                msg = f"{ts} 使用率 {pct:.1f}%"
                details.append(msg)

        # 汇总结论
        if warnings:
            # 拼接详细建议
            return "；".join(warnings) + "。请关注临时表空间使用情况。"
        else:
            return "临时表空间使用率正常。" 

    def _analyze_invalid_objects(self, failure_objects_str):
        """
        解析无效对象信息，判断是否需要关注。
        """
        if not failure_objects_str or '请使用最新的XML文件生成器' in failure_objects_str:
            return "未检测到无效对象。"
        lines = [l for l in failure_objects_str.strip().split('\n') if 'INVALID' in l or 'invalid' in l]
        count = len(lines)
        if count > 0:
            return f"存在 {count} 个无效对象，建议重新编译或删除。"
        else:
            return "所有数据库对象均有效。"

    def _analyze_backup(self, backup_str):
        """
        解析数据库备份配置
        """
        if not backup_str or '请使用最新的XML文件生成器' in backup_str:
            return "未检测到数据库备份配置，建议配置逻辑备份或物理备份。"
        lower_str = backup_str.lower()
        if any(keyword in lower_str for keyword in ['expdp', 'rman', 'dump', 'backup', 'exp']):
            return "已部署备份策略，建议定期验证备份可恢复性。"
        else:
            return "未检测到数据库备份配置，建议配置逻辑备份或物理备份。"

    def _generate_mem_pie_chart(self, total_gb, sys_used_pct, app_used_pct):
        """
        生成内存使用饼图
        :param total_gb: 总内存（GB）
        :param sys_used_pct: 系统已用内存（%）
        :param app_used_pct: 应用已用内存（%）
        :return: 内存使用饼图的字节流
        """
        other_used_pct = sys_used_pct - app_used_pct
        free_pct = 100 - sys_used_pct

        labels = ['应用内存', '系统其他内存', '空闲内存']
        sizes = [app_used_pct, other_used_pct, free_pct]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        explode = (0.05, 0, 0)

        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        plt.figure(figsize=(6, 4))
        plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', startangle=90, shadow=True)
        plt.title(f'主机内存使用概况 (总计: {total_gb:.2f} GB)', fontsize=12)
        plt.axis('equal')

        img_stream = io.BytesIO()
        plt.savefig(img_stream, format='png', dpi=100, bbox_inches='tight')
        img_stream.seek(0)
        plt.close()
        return img_stream

    def _generate_cpu_bar_chart(self, cpu_usage_str):
        """
        生成CPU使用柱状图
        :param cpu_usage_str: CPU使用率字符串，格式为 "us 10.0% sy 20.0% ni 5.0% id 60.0% wa 10.0% hi 5.0% si 5.0% st 5.0%"
        :return: CPU使用柱状图的字节流
        """
        pattern = r'(\d+\.?\d*)%?\s*(us|sy|ni|id|wa|hi|si|st)'
        matches = re.findall(pattern, cpu_usage_str)
        data = {key: float(val) for val, key in matches}

        categories = ['us', 'sy', 'ni', 'id', 'wa', 'hi', 'si', 'st']
        labels = ['用户', '系统', 'Nice', '空闲', 'I/O 等待', '硬件中断', '软件中断', 'Steal']
        values = [data.get(cat, 0.0) for cat in categories]

        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD', '#D4A5A5', '#9859B6', '#3498DB']
        plt.figure(figsize=(8, 2))
        left = 0
        for i, (val, label, col) in enumerate(zip(values, labels, colors)):
            plt.barh(['CPU 使用率'], val, left=left, color=col, label=label)
            left += val
        plt.xlim(0, 100)
        plt.xlabel('百分比 (%)')
        plt.title('CPU 使用率分解')
        plt.legend(loc='lower right', fontsize=8)
        plt.tight_layout()

        img_stream = io.BytesIO()
        plt.savefig(img_stream, format='png', dpi=100, bbox_inches='tight')
        img_stream.seek(0)
        plt.close()
        return img_stream

    def _generate_disk_bar_chart(self, disk_used_human_str):
        """
        生成磁盘使用柱状图
        :param disk_used_human_str: 磁盘使用率字符串，格式为 "Filesystem 10.0% /dev/sda1 100.0% /dev/sda2 50.0% /dev/sda3 25.0%"
        :return: 磁盘使用柱状图的字节流
        """
        lines = disk_used_human_str.strip().split('\n')
        mount_points = []
        used_pcts = []

        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                continue
            mount = parts[0]
            match = re.search(r'Use%:(\d+(?:\.\d+)?)%', line)
            if match:
                pct = float(match.group(1))
                mount_points.append(mount)
                used_pcts.append(pct)

        if not mount_points:
            return None

        plt.figure(figsize=(8, max(3, len(mount_points)*0.6)))
        bars = plt.barh(mount_points, used_pcts, color='#5D9CEC')
        plt.xlabel('使用率 (%)')
        plt.title('各挂载点磁盘使用率')
        plt.xlim(0, 100)
        for bar, pct in zip(bars, used_pcts):
            plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                     f'{pct:.1f}%', va='center', fontsize=9)
        plt.tight_layout()

        img_stream = io.BytesIO()
        plt.savefig(img_stream, format='png', dpi=100, bbox_inches='tight')
        img_stream.seek(0)
        plt.close()
        return img_stream

    def parsexfl(self, sname, filelist, doc_obj=None, **kwargs):
        """
        解析XML文件，提取数据库信息
        :param sname: 学校名称
        :param filelist: XML文件列表
        :param doc_obj: XML文档对象
        :param kwargs: 其他参数
        :return: 包含数据库信息的字典
        """
        kwargs['schoolname'] = sname
        checktimelist = []
        for file in filelist:
            try:
                checktimelist.append(XmlParser(file).get_member('system now time'))
            except Exception as e:
                print(" * [Error] " + str(e) + "  -->  " + file)
                continue
        kwargs['checkdate'] = max(checktimelist)[:10] if checktimelist else "未知日期"
        kwargs['checkusername'] = kwargs.get('checkusername', '售后运维部')

        kwargs['database_base_check'] = []
        kwargs['database_detail_check'] = []
        kwargs['dynamic_suggestions'] = []

        for file in filelist:
            xp_obj = XmlParser(file)
            try:
                xp_obj.root
            except Exception as e:
                print(" * [Error] " + str(e) + "  -->  " + file)
                continue

            kwargs['database_base_check'].append({
                'appname': xp_obj.get_application,
                'hostname': xp_obj.get_member('hostname'),
                'ipaddr': xp_obj.get_member('ip address'),
                'osversion': xp_obj.get_member('os type') + " " + xp_obj.get_member('os version'),
                'cpu': xp_obj.get_member('cpu processor') + ' threads ' + xp_obj.get_member('cpu model'),
                'mem': xp_obj.get_member('memory total'),
                'databasename': xp_obj.get_member('database name'),
                'instancename': xp_obj.get_member('instance name'),
                'databaseid': xp_obj.get_member('database id'),
                'databaseversion': xp_obj.get_member('database version'),
                'createdtime': xp_obj.get_member('created time'),
                'characterset': xp_obj.get_member('character set'),
                'rac': xp_obj.get_member('israc')
            })

            mem_used_display = xp_obj.get_member('system memory used')
            disk_analysis = self._analyze_disk_usage(xp_obj.get_member('disk used human'))
            cpu_analysis = self._analyze_cpu_usage(xp_obj.get_member('cpu used'))
            mem_analysis = self._analyze_memory_usage(xp_obj.get_member('system memory used'))
            lsnrctl_analysis = self._analyze_lsnrctl_status(xp_obj.get_member('lsnrctl status'))
            archive_analysis = self._analyze_archive_mode(xp_obj.get_member('archive mode'))
            tablespace_analysis = self._analyze_tablespace_usage(xp_obj.get_member('tablespace usage'))
            temptablespace_analysis = self._analyze_temp_tablespace_usage(xp_obj.get_member('temp tablespace usage'))
            invalid_analysis = self._analyze_invalid_objects(xp_obj.get_member('failure objects'))
            backup_analysis = self._analyze_backup(xp_obj.get_member('database backup'))

            kwargs['database_detail_check'].append({
                'appname': xp_obj.get_application,
                'hosts': xp_obj.get_member('local hosts file'),
                'diskused': xp_obj.get_member('disk used human'),
                'cpuused': xp_obj.get_member('cpu used'),
                'memused': mem_used_display,
                'lsnrctlstatus': xp_obj.get_member('lsnrctl status'),
                'alertlog': xp_obj.get_member('alert log'),
                'opatchinfo': xp_obj.get_member('opatch info'),
                'sgainfo': xp_obj.get_member('sga info'),
                'controlfileinfo': xp_obj.get_member('controlfile info'),
                'loginfo': xp_obj.get_member('log info'),
                'archivemode': xp_obj.get_member('archive mode'),
                'tablespaceusage': xp_obj.get_member('tablespace usage'),
                'temptablespaceusage': xp_obj.get_member('temp tablespace usage'),
                'datafileinfo': xp_obj.get_member('datafile info'),
                'dbuserinfo': xp_obj.get_member('dbuser info'),
                'failjobs': xp_obj.get_member('fail jobs'),
                'invalidindexes': xp_obj.get_member('invalid indexes'),
                'failureobjects': xp_obj.get_member('failure objects'),
                'deadlock': xp_obj.get_member('deadlocks'),
                'databasebackup': xp_obj.get_member('database backup'),
                'disk_analysis': disk_analysis,
                'cpu_analysis': cpu_analysis,
                'mem_analysis': mem_analysis,
                'lsnrctl_analysis': lsnrctl_analysis,
                'archive_analysis': archive_analysis,
                'tablespace_analysis': tablespace_analysis,
                'temptablespace_analysis': temptablespace_analysis,
                'invalid_analysis': invalid_analysis,
                'backup_analysis': backup_analysis
            })

            try:
                total_mem_str = xp_obj.get_member('memory total')
                sys_used_str = xp_obj.get_member('system memory used')
                app_used_str = xp_obj.get_member('app memory used')
                if total_mem_str and sys_used_str and app_used_str:
                    total_gb = float(total_mem_str.replace('GB', ''))
                    sys_pct = float(sys_used_str.rstrip('%'))
                    app_pct = float(app_used_str.rstrip('%'))
                    mem_img_stream = self._generate_mem_pie_chart(total_gb, sys_pct, app_pct)
                    if doc_obj:
                        kwargs['mem_chart'] = InlineImage(doc_obj, mem_img_stream, width=Inches(5))
                    else:
                        kwargs['mem_chart_stream'] = mem_img_stream
                else:
                    print(" * [警告] 内存数据缺失，无法生成内存图表")
                    kwargs['mem_chart'] = "内存数据缺失"
            except Exception as e:
                print(" * [警告] 生成内存图表失败: {}".format(e))
                kwargs['mem_chart'] = "无法生成内存图表"

            try:
                cpu_used_str = xp_obj.get_member('cpu used')
                if cpu_used_str and '请使用最新的XML文件生成器2' not in cpu_used_str:
                    cpu_img_stream = self._generate_cpu_bar_chart(cpu_used_str)
                    if doc_obj and cpu_img_stream:
                        kwargs['cpu_chart'] = InlineImage(doc_obj, cpu_img_stream, width=Inches(6))
                    else:
                        kwargs['cpu_chart_stream'] = cpu_img_stream
                else:
                    print(" * [警告] CPU使用率数据缺失或无效")
            except Exception as e:
                print(" * [警告] 生成CPU图表失败: {}".format(e))
                kwargs['cpu_chart'] = "无法生成CPU图表"

            try:
                disk_used_str = xp_obj.get_member('disk used human')
                if disk_used_str and '请使用最新的XML文件生成器2' not in disk_used_str:
                    disk_img_stream = self._generate_disk_bar_chart(disk_used_str)
                    if doc_obj and disk_img_stream:
                        kwargs['disk_chart'] = InlineImage(doc_obj, disk_img_stream, width=Inches(6))
                    else:
                        kwargs['disk_chart_stream'] = disk_img_stream
                else:
                    print(" * [警告] 磁盘使用率数据缺失或无效")
            except Exception as e:
                print(" * [警告] 生成磁盘图表失败: {}".format(e))
                kwargs['disk_chart'] = "无法生成磁盘图表"

        #total_issues = 0
        critical_issues = 0
        warning_issues = 0

        for item in kwargs['database_detail_check']:
            if "严重偏高" in item.get('disk_analysis', ''):
                critical_issues += 1
            elif "较高" in item.get('disk_analysis', '') or "接近阈值" in item.get('disk_analysis', ''):
                warning_issues += 1
            if "负载过高" in item.get('cpu_analysis', ''):
                critical_issues += 1
            elif "负载较高" in item.get('cpu_analysis', ''):
                warning_issues += 1
            if "严重不足" in item.get('mem_analysis', ''):
                critical_issues += 1
            elif "较高" in item.get('mem_analysis', ''):
                warning_issues += 1
            if "未开启数据库监听" in item.get('lsnrctl_analysis', ''):
                warning_issues += 1
            if "未开启归档模式" in item.get('archive_analysis', ''):
                warning_issues += 1
            #if "表空间不足" in item.get('tablespace_analysis', ''):
            #    warning_issues += 1
            #if "临时表空间不足" in item.get('temptablespace_analysis', ''):
            #    warning_issues += 1
            #if "存在" in item.get('invalid_analysis', '') and "无效对象" in item.get('invalid_analysis', ''):
            #    warning_issues += 1
            if "未检测到数据库备份配置" in item.get('backup_analysis', ''):
                critical_issues += 1

        if critical_issues > 0:
            dynamic_conclusion = f"本次巡检发现 {critical_issues} 项严重问题，{warning_issues} 项警告，建议立即处理严重问题。"
        elif warning_issues > 0:
            dynamic_conclusion = f"本次巡检发现 {warning_issues} 项警告，整体性能尚可，但建议关注并优化。"
        else:
            dynamic_conclusion = "本次巡检未发现明显问题，总体性能良好。"

        kwargs['dynamic_conclusion'] = dynamic_conclusion

        from collections import defaultdict
        app_suggestions = defaultdict(list)

        for item in kwargs['database_detail_check']:
            appname = item['appname']
            if "严重偏高" in item['disk_analysis']:
                app_suggestions[appname].append(item['disk_analysis'])
            if "负载过高" in item['cpu_analysis']:
                app_suggestions[appname].append(item['cpu_analysis'])
            if "严重不足" in item['mem_analysis']:
                app_suggestions[appname].append(item['mem_analysis'])
            if "未开启数据库监听" in item['lsnrctl_analysis']:
                app_suggestions[appname].append(item['lsnrctl_analysis'])
            if "未开启归档模式" in item['archive_analysis']:
                app_suggestions[appname].append(item['archive_analysis'])
            #if "表空间不足" in item['tablespace_analysis']:
            #    app_suggestions[appname].append(item['tablespace_analysis'])
            #if "临时表空间不足" in item['temptablespace_analysis']:
            #    app_suggestions[appname].append(item['temptablespace_analysis'])
            #if "存在" in item['invalid_analysis'] and "无效对象" in item['invalid_analysis']:
            #    app_suggestions[appname].append(item['invalid_analysis'])
            if "未检测到数据库备份配置" in item['backup_analysis']:
                app_suggestions[appname].append(item['backup_analysis'])

        dynamic_suggestions = []
        for appname, advice_list in app_suggestions.items():
            unique_advice = list(dict.fromkeys(advice_list))
            dynamic_suggestions.append({
                'appname': appname,
                'advice_list': unique_advice
            })

        if not dynamic_suggestions:
            dynamic_suggestions.append({
                'appname': '系统',
                'advice_list': ['本次巡检未发现明显问题，总体状态良好。']
            })

        kwargs['dynamic_suggestions'] = dynamic_suggestions
        return kwargs

    def output(self, outpath, username=None):
        """
        生成数据库巡检报告
        :param outpath: 输出路径
        :param username: 巡检人员姓名
        :return: None
        """
        outpath_abs = op.abspath(outpath)
        os.makedirs(outpath_abs, exist_ok=True)

        if username is None:
            username = input("请输入巡检人员姓名：").strip()
        if username == '':
            username = '售后运维部'

        for sname, filelist in self.filedict.items():
            if not filelist:
                print(f"警告：学校 {sname} 没有有效的 XML 文件，跳过报告生成")
                continue

            self.doc = DocxTemplate("database_template.docx")
            context = self.parsexfl(sname, filelist, doc_obj=self.doc, checkusername=username)
            for stream_key in ['mem_chart_stream', 'cpu_chart_stream', 'disk_chart_stream']:
                if stream_key in context and context[stream_key] is not None:
                    chart_key = stream_key.replace('_stream', '')
                    try:
                        context[chart_key] = InlineImage(self.doc, context[stream_key], width=Inches(5))
                        del context[stream_key]
                    except Exception as e:
                        print(" * [错误] 无法插入图表 {}: {}".format(chart_key, e))
                        context[chart_key] = "图表插入失败"
            self.doc.render(context)
            checkdate = context.get('checkdate', '未知日期')
            if '-' in checkdate:
                year_month = checkdate.split('-', 2)[0] + '-' + checkdate.split('-', 2)[1]
            else:
                year_month = checkdate
            filename = f"{year_month}{sname}数据库巡检报告.doc"
            out_file = op.join(outpath_abs, filename)
            try:
                self.doc.save(out_file)
            except PermissionError as e:
                print(f"错误：无法保存文件 {out_file}，请确认文件未被其他程序打开，且当前用户有写入权限。")
                raise e
            print(f"已生成报告：{out_file}")
        return None
