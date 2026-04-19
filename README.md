# StructPage2MD

`StructPage2MD` 用来把结构化网页内容整理成更适合归档和后续处理的数据文件。

这次已经把原来分散在 `01` 和 `04` 的两部分能力整合到了新的 [05webtomd_faq_pipeline.py](./05webtomd_faq_pipeline.py)：

- 网页正文提取并转换为 Markdown
- 高频 FAQ 问答对提取并导出为 JSON / Markdown
- 输出文件统一写入 `data/` 目录

## 当前脚本说明

- `01titlemap.py`
  早期版本：抓取网页并转换为 Markdown。
- `04merge2_3.py`
  早期版本：渲染页面并抽取 FAQ。
- `05webtomd_faq_pipeline.py`
  一体化版本：同时完成网页转 Markdown 与 FAQ 提取，并统一输出目录。

## 目录结构

```text
webTomd/
├─ 01titlemap.py
├─ 02webtomd_extract_html.py
├─ 03extract_faq.py
├─ 04merge2_3.py
├─ 05webtomd_faq_pipeline.py
├─ data/
│  ├─ baidu_yidian_raw.html
│  ├─ baidu_yidian.md
│  ├─ faq_rendered_snapshot.html
│  ├─ faq_qa.json
│  └─ faq_qa.md
└─ README.md
```

## 依赖

基础运行：

```bash
pip install requests beautifulsoup4
```

如果你希望脚本直接在线渲染页面并抓 FAQ，还需要：

```bash
pip install playwright
playwright install chromium
```

## 使用方式

### 1. 标准运行

有 Playwright 时，直接执行：

```bash
python 05webtomd_faq_pipeline.py
```

默认会：

- 抓取网页原始 HTML
- 生成网页 Markdown
- 渲染页面并抽取 FAQ
- 将结果统一写入 `data/`

### 2. 离线测试 / 使用已有 HTML

如果本地已经保存了原始 HTML 和渲染后 HTML，可以直接离线跑：

```bash
python 05webtomd_faq_pipeline.py ^
  --source-html .\baidu_yidian_raw1.html ^
  --rendered-html .\faq_rendered_snapshot1.html ^
  --output-dir .\data
```

这个模式适合：

- 没装 Playwright 时先验证流程
- 使用已有样本页面复现输出
- 调试 FAQ 解析逻辑

## 输出文件

运行完成后，默认会在 `data/` 下生成：

- `baidu_yidian_raw.html`：原始网页 HTML
- `baidu_yidian.md`：整理后的网页 Markdown
- `faq_rendered_snapshot.html`：FAQ 抽取所用的渲染后 HTML
- `faq_qa.json`：FAQ 问答对 JSON
- `faq_qa.md`：FAQ 问答对 Markdown

## 说明

- FAQ 抽取对页面结构有一定依赖，如果百度页面类名变化，需要同步更新选择器。
- 当前项目保留 `01` 到 `04` 作为历史脚本，后续推荐优先使用 `05`。
