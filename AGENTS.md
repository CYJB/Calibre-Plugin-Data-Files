# AGENTS.md

给维护者 / AI agent 看的实现笔记；面向用户的说明在 [README.md](README.md)。

## 文件职责

| 文件 | 作用 |
| --- | --- |
| `__init__.py` | 插件类（`InterfaceActionBase`）：名称、版本、`actual_plugin`、配置入口 |
| `action.py` | 扫描 `data/` 目录、按配置过滤、生成 `<tr>`、包装 `render_html`、刷新动作 |
| `config.py` | `JSONConfig('plugins/book_data_files.json')`、扩展名归一化 |
| `ui.py` | 配置对话框（扩展名、显示大小、显示修改时间） |
| `plugin-import-name-book_data_files.txt` | 空文件，仅文件名生效，让 calibre 以 `calibre_plugins.book_data_files` 加载 |

## 依赖的 calibre 内部机制（9.17.0 确认）

### 详情面板的渲染

`calibre.gui2.book_details.render_html(mi, vertical, widget, ...)` 返回
`(html, table, comments)`；`BookInfo.show_data()` 按**模块级名字**调用它，再把 html
`setHtml()` 进面板。`render_parts(table, comments, vertical)` 负责拼最终 HTML。

插件在 InterfaceAction 的 `genesis()` 里把 `book_details.render_html` 换成包装函数：
先调用原函数，再把数据文件行插到 `table` 的 `</table>` 之前，最后用
`render_parts()` 重新拼 HTML。这样详情面板和书籍详情弹窗都会生效，且只改显示，
不读书库、不写数据库、不改 metadata。

### 点击 `data/` 链接打开文件

`BookInfo.link_activated()` 只把 `http/https` 直接交给 `safe_open_url()`，其余链接
用 `link.toString(NO_URL_FORMATTING)` 原样发出，进入
`BookDetails.handle_click_from_popup()`；后者的 `browse()`：

```python
if url.startswith(DATA_DIR_NAME + '/'):          # DATA_DIR_NAME == 'data'
    path = os.path.join(db.abspath(book_id), url)
    qurl = QUrl.fromLocalFile(path)
else:
    qurl = QUrl(url, QUrl.TolerantMode)
safe_open_url(qurl)
```

`book_id` 取自 `BookDetails.last_data['book_id']`（当前显示的书），因此链接必须是
相对书目录的 `data/<相对路径>`：用 `/` 分隔，不要 `./` 或 `file://` 前缀。
路径里的中文和空格不需要转义（`QUrl` 的 tolerant 解析 + `NO_URL_FORMATTING` 会还原）。

`safe_open_url()` 对 `file` / 空 scheme 会拒绝这些扩展名后直接返回：
`.exe .com .cmd .bat .sh .psh .ps1 .vbs .js .wsf .vba .py .rb .pl .app`；
其余文件交给 `open_url()`（系统默认程序）。

### 打补丁的坑

* 详情弹窗模块 `calibre.gui2.dialogs.book_info` 在导入时把 `render_html` 绑成了
  模块级名字；如果它已经导入，要一并替换（`install_patch()` 里通过 `sys.modules` 处理）。
* `install_patch()` 用函数属性 `_book_data_files_patched` 保证幂等，重复
  `genesis()` 不会套两层。
* `BookInfo.last_rendered_html` 保存 `(html, table, comments)` 供切换横/竖布局时重新
  `render_parts()`，所以包装函数返回的 `table` 必须是完整表格字符串。
* 竖向布局时 `table` 和 `comments` 拼在一起；横向布局外面还套一层表格，所以改完
  `table` 必须重新 `render_parts()` 生成 html，不能直接字符串替换 html。

## 打包

* zip 根目录放 `__init__.py` 等文件；安装后 loader 以 `calibre_plugins.book_data_files`
  导入，`actual_plugin` 指向 `calibre_plugins.book_data_files.action:BookDataFilesAction`。
* `plugin-import-name-*.txt` 只读取文件名，内容为空即可；没有它时 import 名会是
  `calibre_plugins.dummyN`，`actual_plugin` 就对不上。
* 开发时可用 `calibre-customize -b <本目录>` 打包并安装。

## 配置存储

`JSONConfig('plugins/book_data_files.json')`：

| 键 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `extensions` | str | `''` | 逗号分隔白名单，空 = 全部；`*.pdf`、`.jpg` 会被归一化 |
| `show_size` | bool | `True` | 与 `calibre.human_readable()` 输出一致（截断到 1 位小数） |
| `show_mtime` | bool | `False` | `YYYY-MM-DD HH:MM` |

## 自测方法

测试脚本不在仓库里，开发时的 headless 验证要点：

* `calibre-debug -e <script>` 运行脚本（`calibre-debug` 在 calibre 安装目录下）；
* 设置一个**可写**的 `CALIBRE_CONFIG_DIRECTORY`，否则 calibre 会去写
  `%APPDATA%\calibre`（沙箱/CI 里通常会失败）；
* `QT_QPA_PLATFORM=offscreen` + `calibre.gui2.Application([])` 可在无窗口环境创建
  `BookInfo` 控件；
* 先 `calibre.customize.zipplugin.loader.load(zip)` 注册 `calibre_plugins.*`，再导入
  `calibre_plugins.book_data_files.action`，即可直接测 `data_files_rows()`；
* 用假的 `db_for_mi` / `FakeDB` 调真实 `render_html`，可验证面板 HTML；锚点可用
  `QTextDocument` 遍历 `charFormat().anchorHref()` 检查，确认是相对 `data/...`；
* `do_user_config()` 可把 `ConfigDialog.exec` 换掉，验证保存/取消行为。

## 升级适配

calibre 大版本升级时重点确认：

* `render_html()` 是否仍返回 `(html, table, comments)`，`render_parts()` 签名是否变化；
* `handle_click_from_popup()` 里 `data/` 前缀的处理是否仍在；
* `safe_open_url()` 的可执行文件黑名单是否变化；
* `calibre.db.constants.DATA_DIR_NAME` 是否仍为 `data`。

## 不装插件的替代做法

calibre 自带：在书籍评论里写指向 `data/` 的链接也能点击打开：

```html
<p><a href="data/a.pdf">a.pdf</a></p>
<p><a href="data/封面原图.jpg">封面原图.jpg</a></p>
```

缺点是列表要手动维护，而且评论属于元数据，会写进书库。
