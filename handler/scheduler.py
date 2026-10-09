# -*- coding: utf-8 -*-
"""
统一巡检报告生成调度脚本
依次生成服务器巡检报告和数据库巡检报告，遇到错误时输出并暂停。

@author: Ryan和他的小伙伴们
@date: 2026-06-16
@version: 2.0
"""

from folder_handler import FolderParser
from server_word_handler import ServerWordHandler
from database_word_handler import DatabaseWordHandler


def generate_server_report(username):
    """生成服务器巡检报告"""
    print("\n" + "="*50)
    print("开始生成服务器巡检报告...")
    print("="*50)

    try:
        fp_obj = FolderParser(r'../system_check/logs', xml_prefix='system_check_')
        filedict = fp_obj.get_latest_log()

        if not filedict:
            print("警告：未找到服务器巡检XML文件，跳过服务器报告生成")
            return True

        wh_obj = ServerWordHandler(filedict)
        wh_obj.output(r'../check_report', username=username)
        print("服务器巡检报告生成完毕")
        return True
    except Exception as e:
        print(f"\n[错误] 服务器巡检报告生成失败：{e}")
        return False


def generate_database_report(username):
    """生成数据库巡检报告"""
    print("\n" + "="*50)
    print("开始生成数据库巡检报告...")
    print("="*50)

    try:
        fp_obj = FolderParser(r'../oracle_check/logs', xml_prefix='oracle_check_')
        filedict = fp_obj.get_latest_log()

        if not filedict:
            print("警告：未找到数据库巡检XML文件，跳过数据库报告生成")
            return True

        wh_obj = DatabaseWordHandler(filedict)
        wh_obj.output(r'../check_report', username=username)
        print("数据库巡检报告生成完毕")
        return True
    except Exception as e:
        print(f"\n[错误] 数据库巡检报告生成失败：{e}")
        return False


if __name__ == '__main__':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("="*50)
    print("巡检报告生成系统")
    print("="*50)

    # 输入巡检人员姓名（只输入一次）
    username = input("\n请输入巡检人员姓名：").strip()
    if username == '':
        username = '售后运维部'
    print(f"巡检人员：{username}")

    # 先生成服务器报告
    server_success = generate_server_report(username)

    # 如果服务器报告生成失败，暂停并等待用户确认
    if not server_success:
        print("\n" + "="*50)
        print("服务器报告生成过程中出现错误")
        print("="*50)
        input("按回车键继续生成数据库报告，或按 Ctrl+C 取消...")
    else:
        # 服务器报告成功，继续生成数据库报告
        pass

    # 生成数据库报告
    db_success = generate_database_report(username)

    # 如果数据库报告生成失败，暂停
    if not db_success:
        print("\n" + "="*50)
        print("数据库报告生成过程中出现错误")
        print("="*50)
        input("按回车键结束，或按 Ctrl+C 取消...")
    else:
        print("\n" + "="*50)
        print("所有报告生成完毕")
        print("="*50)
