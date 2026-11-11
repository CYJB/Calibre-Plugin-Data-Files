#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把书籍 data 目录里的文件列进书籍详情面板。

实现要点见 AGENTS.md；这里只有两件事：

1. :func:`data_files_rows` 扫描书籍的 data 目录，按配置过滤并生成 ``<tr>``；
2. :func:`install_patch` 包装 ``calibre.gui2.book_details.render_html``，
   把这些行拼到详情表格末尾。
"""

import os
import sys
from datetime import datetime

from calibre import human_readable, prepare_string_for_xml
from calibre.gui2.actions import InterfaceAction

from .config import allowed_extensions, is_allowed, prefs

#: 第一行显示的标签，想换文字改这里即可
DATA_LABEL = '数据文件'

#: 文件太多时最多列多少行，避免详情面板被几百个文件撑爆
MAX_FILES = 300


def data_files_rows(mi):
    """返回详情表格里要追加的 HTML 行，没有 data 目录（或没有文件）时返回 ''。"""
    path = getattr(mi, 'path', None)
    if not path or getattr(mi, 'id', None) is None:
        return ''
    if isinstance(path, bytes):
        path = path.decode(sys.getfilesystemencoding() or 'utf-8', 'replace')
    data_dir = os.path.join(path, 'data')
    if not os.path.isdir(data_dir):
        return ''

    allowed = allowed_extensions()
    found = []
    hidden = 0
    for dirpath, dirnames, filenames in os.walk(data_dir):
        dirnames[:] = sorted((d for d in dirnames if not d.startswith('.')), key=str.lower)
        for fname in sorted(filenames, key=str.lower):
            if fname.startswith('.'):
                continue
            full = os.path.join(dirpath, fname)
            if not os.path.isfile(full):
                continue
            if not is_allowed(fname, allowed):
                hidden += 1
                continue
            try:
                st = os.stat(full)
            except OSError:
                continue
            # 相对书目录的路径，统一用 / 分隔；点击时 calibre 会用 os.path.join 拼回去
            rel = os.path.relpath(full, path).replace(os.sep, '/')
            found.append((rel.lower(), rel, full, st.st_size, st.st_mtime))
    if not found and not hidden:
        return ''

    found.sort(key=lambda x: x[0])
    esc = prepare_string_for_xml
    show_size = bool(prefs['show_size'])
    show_mtime = bool(prefs['show_mtime'])
    rows = []
    for i, (_, rel, full, size, mtime) in enumerate(found[:MAX_FILES]):
        meta = []
        if show_size:
            # 与 calibre 模板函数 {xxx:human_readable()} 用的同一个实现
            meta.append(human_readable(size))
        if show_mtime:
            try:
                meta.append(datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M'))
            except (OSError, OverflowError, ValueError):
                pass
        meta_html = ''
        if meta:
            meta_html = ' <span style="color: palette(placeholder-text); font-size: smaller">%s</span>' % esc(' · '.join(meta))
        # 行首标签只显示一次，其余行留空，保持表格左列干净
        label = DATA_LABEL if i == 0 else ''
        rows.append(
            '<tr id="data_files_%d" class="datatype_text">'
            '<td class="title">%s</td>'
            '<td class="value">'
            '<a href="%s" title="%s">%s</a>%s'
            '</td></tr>'
            % (
                i,
                esc(label),
                esc(rel, attribute=True),
                esc(full, attribute=True),
                esc(rel.partition('data/')[2] or rel),
                meta_html,
            )
        )
    if len(found) > MAX_FILES:
        rows.append(
            '<tr id="data_files_more" class="datatype_text"><td class="title"></td>'
            '<td class="value"><i>另有 %d 个文件未显示</i></td></tr>' % (len(found) - MAX_FILES)
        )
    if hidden:
        # 被文件类型配置过滤掉的文件也提示一下，免得以为文件丢了
        label = '' if rows else DATA_LABEL
        rows.append(
            '<tr id="data_files_hidden" class="datatype_text">'
            '<td class="title">%s</td>'
            '<td class="value"><i>%d 个文件因文件类型设置未显示</i></td></tr>'
            % (prepare_string_for_xml(label), hidden)
        )
    return ''.join(rows)


def install_patch():
    """给 render_html 装上包装。重复调用是安全的。"""
    import calibre.gui2.book_details as bd

    if getattr(bd.render_html, '_book_data_files_patched', False):
        return

    original = bd.render_html

    def render_html(mi, vertical, widget, *args, **kwargs):
        html, table, comments = original(mi, vertical, widget, *args, **kwargs)
        try:
            rows = data_files_rows(mi)
        except Exception:
            import traceback

            traceback.print_exc()
            rows = ''
        if rows:
            end = table.rfind('</table>')
            if end >= 0:
                table = table[:end] + rows + table[end:]
                # 横向布局时 html 里还套了一层外表格，直接重新拼最稳
                html = bd.render_parts(table, comments, vertical)
        return html, table, comments

    render_html._book_data_files_patched = True
    bd.render_html = render_html

    # 书籍详情弹窗（双击书籍详情打开的那个窗口）在导入时就把 render_html
    # 绑成了模块级名字；如果它已经导入过，要一并替换。
    dlg = sys.modules.get('calibre.gui2.dialogs.book_info')
    if dlg is not None and getattr(dlg, 'render_html', None) is original:
        dlg.render_html = render_html


class BookDataFilesAction(InterfaceAction):
    """本身不需要按钮，只是借 calibre 加载 InterfaceAction 的时机打补丁。

    顺带提供一个「刷新书籍详情」的动作：外部往 data 目录里加了文件之后，
    切换一下书籍或触发它，面板就会重新生成列表。
    """

    name = 'Book Data Files'
    action_spec = ('刷新书籍详情', None, '重新读取当前书籍的 data 目录并刷新详情面板', None)
    action_type = 'current'

    def genesis(self):
        try:
            install_patch()
        except Exception:
            import traceback

            traceback.print_exc()
        self.qaction.triggered.connect(self.refresh_book_details)

    def refresh_book_details(self):
        view = self.gui.current_view()
        if view is None:
            return
        try:
            view.refresh_book_details()
        except Exception:
            import traceback

            traceback.print_exc()
