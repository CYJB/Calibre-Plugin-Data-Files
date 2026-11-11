#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""插件配置：决定哪些文件类型的文件显示在书籍详情面板里。

配置存在 calibre 配置目录的 ``plugins/book_data_files.json`` 里：

* ``extensions`` —— 逗号分隔的扩展名白名单；留空表示显示 data 目录中的全部文件。
  写 ``pdf, jpg``、``*.pdf, .jpg`` 都能识别。
"""

import os

from calibre.utils.config import JSONConfig

prefs = JSONConfig('plugins/book_data_files')

#: 默认显示全部文件，保持"装上就有东西看"的行为
prefs.defaults['extensions'] = ''
#: 文件大小（默认显示）
prefs.defaults['show_size'] = True
#: 修改时间（默认不显示）
prefs.defaults['show_mtime'] = False


def split_extensions(raw):
    """把 'pdf, *.jpg; .png' 这样的字符串规范化成 ['pdf', 'jpg', 'png']。"""
    ans = []
    for part in str(raw or '').replace(';', ',').replace('\n', ',').split(','):
        part = part.strip().lower()
        if part.startswith('*.'):
            part = part[2:]
        part = part.lstrip('.')
        if part and part not in ans:
            ans.append(part)
    return ans


def allowed_extensions():
    """当前配置允许的扩展名集合；空集合表示不限。"""
    return set(split_extensions(prefs['extensions']))


def file_extension(name):
    ext = os.path.splitext(name)[1].lower()
    return ext[1:] if ext.startswith('.') else ext


def is_allowed(name, allowed=None):
    if allowed is None:
        allowed = allowed_extensions()
    return not allowed or file_extension(name) in allowed


def format_extensions():
    return ', '.join(split_extensions(prefs['extensions']))
