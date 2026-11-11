#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Book Data Files — 在 calibre 的书籍详情面板里列出书籍 data 目录中的文件。

一个文件一行，点击文件名用系统默认程序打开；在插件配置里可以选择显示哪些
文件类型，以及是否显示大小 / 修改时间。

用户说明见 README.md，实现细节见 AGENTS.md。
"""

from calibre.customize import InterfaceActionBase


class BookDataFiles(InterfaceActionBase):
    name = 'Book Data Files'
    description = '在书籍详情面板中按行列出书籍 data 目录里的文件，点击文件名直接打开。'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'CYJB'
    version = (1, 0, 0)
    minimum_calibre_version = (6, 0, 0)
    actual_plugin = 'calibre_plugins.book_data_files.action:BookDataFilesAction'

    def is_customizable(self):
        # 首选项 → 插件 → Book Data Files → 自定义插件，会调用 do_user_config()
        return True

    def do_user_config(self, parent=None):
        from qt.core import QDialog

        from .ui import ConfigDialog

        d = ConfigDialog(parent)
        if d.exec() == QDialog.DialogCode.Accepted:
            self._refresh_book_details()
        return None

    @staticmethod
    def _refresh_book_details():
        try:
            from calibre.gui2.ui import get_gui

            gui = get_gui()
            if gui is not None:
                gui.current_view().refresh_book_details()
        except Exception:
            import traceback

            traceback.print_exc()

