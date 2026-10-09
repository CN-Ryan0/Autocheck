# -*- coding: utf-8 -*-
"""
文件夹解析模块
用于遍历日志目录结构，获取各项目、各主机下的最新 XML 日志文件。

@author: Ryan和他的小伙伴们
@date: 2026-10-09
@version: 2.1
"""

import os
from os import path as op
import re


class FolderParser:
    """解析日志文件夹，提供获取项目、主机及最新 XML 文件的功能"""

    def __init__(self, sourcepath, xml_prefix='system_check_'):
        """
        初始化，读取基础目录下的所有项目（一级子目录）
        :param sourcepath: 日志根目录路径
        :param xml_prefix: XML 文件名前缀，如 'system_check_' 或 'oracle_check_'
        """
        self.xml_prefix = xml_prefix
        self.xml_suffix = '.xml'
        self.basedir = op.abspath(sourcepath)
        try:
            self.get_all_project = os.listdir(self.basedir)
        except FileNotFoundError as e:
            print(f"错误：目录不存在 - {e}")
            import sys
            sys.exit(1)
        except PermissionError as e:
            print(f"错误：无权限读取目录 - {e}")
            import sys
            sys.exit(1)

    def _get_latest_xml_in_dir(self, dirpath):
        """从指定目录中获取最新的 XML 文件名"""
        if not op.isdir(dirpath):
            return None

        try:
            files = os.listdir(dirpath)
        except PermissionError:
            print(f"警告：无权限访问目录 {dirpath}")
            return None

        pattern = re.compile(r'^{}\d+{}$'.format(self.xml_prefix, self.xml_suffix))
        matched = [f for f in files if pattern.match(f)]

        if not matched:
            return None

        matched.sort(key=lambda f: int(f[len(self.xml_prefix):-len(self.xml_suffix)]))
        return matched[-1]

    def get_latest_log(self, projectnames=None, hosts=None, format='path'):
        """
        获取指定项目、主机的最近一次巡检日志文件路径或文件名。
        :param projectnames: 项目名称（字符串或字符串列表），None 表示所有项目
        :param hosts: 主机标识（字符串或字符串列表），None 表示该项目下的所有主机
        :param format: 返回格式：'path' 返回完整路径，'name' 仅返回文件名
        :return: 字典 {项目名: [文件路径/文件名列表]}
        """
        result = {}

        if projectnames is None:
            project_list = self.get_all_project
        else:
            project_list = [projectnames] if isinstance(projectnames, str) else list(projectnames)

        if hosts is not None:
            host_filter = [hosts] if isinstance(hosts, str) else list(hosts)
        else:
            host_filter = None

        for projectname in project_list:
            project_path = op.join(self.basedir, projectname)
            if not op.isdir(project_path):
                print(f"警告：项目目录不存在 - {project_path}")
                continue

            try:
                all_hosts = os.listdir(project_path)
            except PermissionError:
                print(f"警告：无法读取项目目录 - {project_path}")
                continue

            if host_filter is None:
                target_hosts = all_hosts
            else:
                target_hosts = [h for h in all_hosts if h in host_filter]

            file_list = []
            for host in target_hosts:
                host_dir = op.join(project_path, host)
                latest_name = self._get_latest_xml_in_dir(host_dir)
                if latest_name is None:
                    continue
                if format == 'path':
                    file_list.append(op.join(host_dir, latest_name))
                else:
                    file_list.append(latest_name)

            if file_list:
                result[projectname] = file_list

        return result

    def get_host(self, *projectnames):
        """获取指定项目（或所有项目）下的主机列表"""
        if projectnames:
            project_list = []
            for arg in projectnames:
                if isinstance(arg, (list, tuple)):
                    project_list.extend(arg)
                else:
                    project_list.append(arg)
        else:
            project_list = self.get_all_project

        result = {}
        for projectname in project_list:
            project_path = op.join(self.basedir, projectname)
            if not op.isdir(project_path):
                print(f"警告：项目目录不存在 - {project_path}")
                continue
            try:
                hosts = os.listdir(project_path)
            except PermissionError:
                print(f"警告：无法读取项目目录 - {project_path}")
                continue
            result[projectname] = hosts

        return result
