#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""插件自己的配置对话框：设置"哪些文件类型显示在书籍详情面板里"。"""

from calibre.utils.localization import _
from qt.core import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QIcon,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from .config import format_extensions, prefs, split_extensions


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('Book Data Files 设置'))
        try:
            self.setWindowIcon(QIcon.ic('plugins.png'))
        except Exception:
            pass

        self.l = l = QVBoxLayout(self)

        intro = QLabel(
            _('只显示这些扩展名的文件（逗号分隔，例如 <b>pdf, jpg, png</b>）。<br>留空表示显示 data 目录中的所有文件。'),
            self,
        )
        intro.setWordWrap(True)
        l.addWidget(intro)

        self.extensions = QLineEdit(format_extensions(), self)
        self.extensions.setPlaceholderText('pdf, jpg, png, txt')
        self.extensions.setToolTip(_('扩展名用逗号分隔；*.pdf、.pdf、PDF 都可以'))
        l.addWidget(self.extensions)

        self.show_size = QCheckBox(_('显示文件大小'), self)
        self.show_size.setChecked(bool(prefs['show_size']))
        self.show_size.setToolTip(_('大小用 calibre 的 human_readable() 格式化，例如 1.4 KB、1.1 MB'))
        l.addWidget(self.show_size)

        self.show_mtime = QCheckBox(_('显示修改时间'), self)
        self.show_mtime.setChecked(bool(prefs['show_mtime']))
        l.addWidget(self.show_mtime)

        hint = QLabel(
            _('过滤只影响显示，不会移动或删除 data 目录里的文件。<br>'
              '没有扩展名的文件在设置了过滤后不会显示；子目录里的文件同样适用。'),
            self,
        )
        hint.setWordWrap(True)
        hint.setStyleSheet('color: palette(placeholder-text);')
        l.addWidget(hint)

        self.bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.bb.accepted.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        l.addWidget(self.bb)

    def accept(self):
        prefs['extensions'] = ', '.join(split_extensions(self.extensions.text()))
        prefs['show_size'] = bool(self.show_size.isChecked())
        prefs['show_mtime'] = bool(self.show_mtime.isChecked())
        QDialog.accept(self)
