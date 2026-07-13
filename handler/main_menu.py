# -*- coding: utf-8 -*-
"""
巡检系统主菜单
提供交互式菜单，协调下载、报告生成、清理等功能。

@author: Ryan和他的小伙伴们
@date: 2026-06-25
@version: 1.2
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from remote_downloader import RemoteDownloader
from local_cleaner import LocalCleaner
from scheduler import generate_server_report, generate_database_report


class MainMenu:
    """主菜单"""

    def __init__(self):
        self.downloader = RemoteDownloader()
        self.cleaner = LocalCleaner()

    def show_menu(self):
        """显示菜单"""
        print("\n" + "=" * 50)
        print("=" * 16 + "  巡检报告生成器  " + "=" * 16)
        print("=" * 50)
        print("  1. 下载巡检文件")
        print("  2. 生成巡检报告")
        print("  3. 删除本地旧文件")
        print("  0. 退出")
        print("=" * 50)

    def get_choice(self):
        """获取用户选择"""
        try:
            choice = input("\n请选择操作 [0-3]: ").strip()
            return choice
        except (EOFError, KeyboardInterrupt):
            return '0'

    def handle_download(self):
        """处理下载巡检文件"""
        print("\n" + "=" * 50, flush=True)
        print("  下载巡检文件", flush=True)
        print("=" * 50, flush=True)

        if not self.downloader.test_connection():
            print("\n无法连接到服务器，请检查网络或服务器配置", flush=True)
            input("\n按回车键返回菜单...")
            return

        if not self.downloader.download_all():
            print("\n下载失败，请检查网络或服务器配置", flush=True)
            input("\n按回车键返回菜单...")
            return

        input("\n按回车键返回菜单...")

    def handle_generate_report(self):
        """处理生成巡检报告"""
        print("\n" + "=" * 50)
        print("  生成巡检报告")
        print("=" * 50)

        username = input("\n请输入巡检人员姓名（直接回车使用默认值）: ").strip()
        if username == '':
            username = '售后运维部'
        print("巡检人员：{}".format(username))

        print("\n正在生成服务器巡检报告...")
        server_ok = generate_server_report(username)

        print("\n正在生成数据库巡检报告...")
        db_ok = generate_database_report(username)

        if server_ok and db_ok:
            print("\n" + "=" * 50)
            print("  所有报告生成完毕")
            print("=" * 50)
        else:
            print("\n" + "=" * 50)
            print("  部分报告生成失败，请查看上方错误信息")
            print("=" * 50)

        input("\n按回车键返回菜单...")

    def handle_clean(self):
        """处理删除本地旧文件"""
        print("\n" + "=" * 50)
        print("  删除本地旧文件")
        print("=" * 50)
        print("\n将删除以下目录中的所有文件：")
        print("  - system_check/logs/")
        print("  - ora_check/logs/")

        confirm = input("\n确认删除？(y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消操作")
            input("\n按回车键返回菜单...")
            return

        if self.cleaner.delete_local_xml():
            print("\n旧文件清理完成")
        else:
            print("\n清理失败")

        input("\n按回车键返回菜单...")

    def run(self):
        """运行主循环"""
        while True:
            self.show_menu()
            choice = self.get_choice()

            if choice == '1':
                self.handle_download()
            elif choice == '2':
                self.handle_generate_report()
            elif choice == '3':
                self.handle_clean()
            elif choice == '0':
                print("\n感谢使用，再见！")
                break
            else:
                print("\n无效选择，请输入 0-3")
                input("按回车键继续...")


if __name__ == '__main__':
    menu = MainMenu()
    menu.run()
