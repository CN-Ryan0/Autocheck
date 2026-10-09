# -*- coding: utf-8 -*-
"""
远程 XML 下载模块
负责连接 rsync 服务器并下载巡检 XML 文件。

@author: Ryan和他的小伙伴们
@date: 2026-06-25
@version: 1.2
"""

import os
import subprocess
from os import path as op


class RemoteDownloader:
    """远程 XML 文件下载器"""

    def __init__(self):
        self.rsync_exe = op.join(op.dirname(op.abspath(__file__)), '..', 'cwRsync', 'rsync.exe')
        self.rsync_password = '[yourpassword]'
        self.rsync_host = '[user]@[server_ip]'
        self.rsync_port = 8858
        self.rsync_timeout = 100
        self.rsync_flags = '-vzrtpDl'

        self.base_dir = op.dirname(op.abspath(__file__))
        self.system_logs_dir = op.join(self.base_dir, '..', 'system_check', 'logs')
        self.db_logs_dir = op.join(self.base_dir, '..', 'oracle_check', 'logs')

    def _to_cygwin_path(self, win_path):
        """将 Windows 路径转换为 Cygwin/rsync 可用的格式"""
        cyg_path = win_path.replace('\\', '/')
        cyg_path = cyg_path.replace(':', '')
        return '/cygdrive/' + cyg_path

    def test_connection(self):
        """测试 rsync 服务器连接"""
        print("正在测试服务器连接...", flush=True)

        env = os.environ.copy()
        env['RSYNC_PASSWORD'] = self.rsync_password

        cmd = [
            self.rsync_exe,
            '--list-only',
            '--port={}'.format(self.rsync_port),
            '--timeout={}'.format(self.rsync_timeout),
            '{}::systemxml'.format(self.rsync_host)
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                encoding='utf-8',
                text=True,
                timeout=self.rsync_timeout + 10
            )
            if result.returncode == 0:
                print("连接测试成功", flush=True)
                return True
            else:
                print("连接测试失败：{}".format(result.stderr.strip() if result.stderr else '未知错误'), flush=True)
                return False
        except subprocess.TimeoutExpired:
            print("连接测试超时，请检查网络或服务器配置", flush=True)
            return False
        except FileNotFoundError:
            print("错误：找不到 rsync 程序 - {}".format(self.rsync_exe), flush=True)
            return False
        except Exception as e:
            print("连接测试出错：{}".format(str(e)), flush=True)
            return False

    def download_all(self):
        """下载服务器和数据库巡检 XML 文件"""
        print("\n开始下载数据，请稍等...", flush=True)

        if not self.download_system_xml():
            return False

        if not self.download_db_xml():
            return False

        print("\n数据同步完成", flush=True)
        return True

    def download_system_xml(self):
        """下载服务器巡检 XML"""
        print("\n下载服务器巡检文件...", flush=True)
        return self._download_single(
            remote_module='systemxml',
            local_dir=self.system_logs_dir,
            label='服务器巡检'
        )

    def download_db_xml(self):
        """下载数据库巡检 XML"""
        print("\n下载数据库巡检文件...", flush=True)
        return self._download_single(
            remote_module='dbxml',
            local_dir=self.db_logs_dir,
            label='数据库巡检'
        )

    def _download_single(self, remote_module, local_dir, label):
        """下载单个模块的 XML 文件"""
        env = os.environ.copy()
        env['RSYNC_PASSWORD'] = self.rsync_password

        cyg_path = self._to_cygwin_path(local_dir)
        #print("远程：{}::{}".format(self.rsync_host, remote_module))
        #print("本地：{}".format(cyg_path))

        cmd = [
            self.rsync_exe,
            self.rsync_flags,
            '--port={}'.format(self.rsync_port),
            #'--delete',
            '--timeout={}'.format(self.rsync_timeout),
            '{}::{}'.format(self.rsync_host, remote_module),
            cyg_path
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                #capture_output=True,  #不捕获子进程输出
                #encoding='utf-8',
                #text=True,
                timeout=self.rsync_timeout + 30
            )
            if result.returncode != 0:
                print("\n下载{}文件失败，请检查网络或服务器配置".format(label), flush=True)
                return False
        except subprocess.TimeoutExpired:
            print("\n下载{}文件超时".format(label), flush=True)
            return False
        except Exception as e:
            print("\n下载{}文件出错：{}".format(label, str(e)), flush=True)
            return False

        return True
