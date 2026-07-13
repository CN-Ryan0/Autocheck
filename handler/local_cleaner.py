# -*- coding: utf-8 -*-
"""
本地旧数据清理模块
负责删除本地旧的巡检 XML 文件并重建目录。

@author: Ryan和他的小伙伴们
@date: 2026-06-16
@version: 1.0
"""

import os
import shutil
from os import path as op


class LocalCleaner:
    """本地 XML 文件清理器"""

    def __init__(self):
        self.base_dir = op.dirname(op.abspath(__file__))
        self.system_logs_dir = op.join(self.base_dir, '..', 'system_check', 'logs')
        self.db_logs_dir = op.join(self.base_dir, '..', 'ora_check', 'logs')

    def delete_local_xml(self):
        """删除本地 XML 文件并重建目录"""
        print("正在清理旧的 XML 文件...")

        dirs_to_clean = [
            self.system_logs_dir,
            self.db_logs_dir
        ]

        for dir_path in dirs_to_clean:
            if op.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    print("已删除目录：{}".format(dir_path))
                except Exception as e:
                    print("删除目录失败 {}：{}".format(dir_path, str(e)))
                    return False

            try:
                os.makedirs(dir_path, exist_ok=True)
                print("已创建目录：{}".format(dir_path))
            except Exception as e:
                print("创建目录失败 {}：{}".format(dir_path, str(e)))
                return False

        print("旧文件清理完成")
        return True

    def clean_system_logs(self):
        """仅清理服务器巡检日志目录"""
        return self._clean_single_dir(self.system_logs_dir, '服务器巡检')

    def clean_db_logs(self):
        """仅清理数据库巡检日志目录"""
        return self._clean_single_dir(self.db_logs_dir, '数据库巡检')

    def _clean_single_dir(self, dir_path, label):
        """清理单个目录"""
        print("正在清理{}日志...".format(label))

        if op.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print("已删除{}目录：{}".format(label, dir_path))
            except Exception as e:
                print("删除{}目录失败：{}".format(label, str(e)))
                return False

        try:
            os.makedirs(dir_path, exist_ok=True)
            print("已创建{}目录：{}".format(label, dir_path))
        except Exception as e:
            print("创建{}目录失败：{}".format(label, str(e)))
            return False

        print("{}日志清理完成".format(label))
        return True
