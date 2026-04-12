# StructPage2MD

StructPage2MD 是一个面向**结构化网页内容提取**的 Python 工具。  
它通过 **Playwright** 渲染动态页面，抓取完整 HTML，并将正文内容转换为清晰、可读、适合存档或二次处理的 **Markdown** 文件。

这个项目特别适合以下场景：

- 医疗百科 / 医典类页面抓取
- 动态渲染网页内容转 Markdown
- 知识库原始网页归档
- 后续用于 RAG / 检索 / 文档整理的数据预处理

---

## Features

- 支持 **动态网页渲染**，不再局限于 `requests` 获取的静态 HTML
- 自动保存 **渲染后的原始 HTML**
- 按网页结构抽取正文，而不是粗暴整页转 Markdown
- 支持将“概述、原因、就医、诊断、治疗、日常”等内容整理为**一级标题**
- 支持单独抽取 **患者最常问的问题（FAQ）** 问答对
- 适合后续接入知识库、RAG、搜索索引或内容存档流程

---

## Why this project

很多内容页表面上看是普通网页，但实际内容常常有这些问题：

- 关键内容由前端 JS 动态渲染
- 直接抓 HTML 会漏掉 FAQ、折叠区、懒加载内容
- 整页转 Markdown 会把导航、按钮、广告、推荐内容一起带进去
- 页面明明有清晰的章节结构，但最终导出的文档层级很乱

StructPage2MD 的目标，就是把这类网页转成**更适合阅读和机器处理的 Markdown 文档**。

---

## Supported extraction strategy

当前版本采用以下策略：

1. 使用 Playwright 渲染页面
2. 等待网络稳定并触发懒加载
3. 尝试展开“更多 / 展开全部”等折叠内容
4. 保存渲染后的完整 HTML
5. 基于页面可见文本和 DOM 结构进行章节切分
6. 单独提取 FAQ 问答对
7. 输出结构化 Markdown

---

## Installation

### 1. Clone repository

```bash
git clone https://github.com/yourname/StructPage2MD.git
cd StructPage2MD
```
