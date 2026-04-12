# -*- coding: utf-8 -*-
"""
将百度医典网页抓取为 HTML，并转换成 Markdown 文件
同时把：
概述、原因、就医、诊断、治疗、日常
映射成 Markdown 一级标题

安装依赖：
    pip install requests beautifulsoup4 markdownify lxml
"""

import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


URL = "https://www.baidu.com/bh/dict/ydxx_7971341401879355500?contentid=ydxx_7971341401879355500&sf_ch=ch_baike&from=dicta&isPageHome=1"
HTML_OUTPUT = "baidu_yidian_raw.html"
MD_OUTPUT = "baidu_yidian.md"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.baidu.com/",
}

SECTION_TITLES = ["概述", "原因", "就医", "诊断", "治疗", "日常"]


def fetch_html(url: str) -> str:
    """抓取网页 HTML"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding

    return resp.text


def save_text(content: str, file_path: str) -> None:
    Path(file_path).write_text(content, encoding="utf-8")


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """清理无关标签"""
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "form", "button", "input"]):
        tag.decompose()

    return soup


def pick_main_content(soup: BeautifulSoup):
    """
    尽量选正文区域；找不到就退回 body
    """
    candidates = [
        {"id": re.compile(r"(content|main|article|detail|lemma)", re.I)},
        {"class_": re.compile(r"(content|main|article|detail|lemma|body)", re.I)},
        {"attrs": {"role": "main"}},
    ]

    for rule in candidates:
        try:
            node = soup.find(**rule)
            if node and len(node.get_text(strip=True)) > 200:
                return node
        except Exception:
            pass

    return soup.body if soup.body else soup


def normalize_special_headings(markdown: str) -> str:
    """
    把【概述、原因、就医、诊断、治疗、日常】规范成 Markdown 一级标题
    兼容这些情况：
    - 概述
    - # 概述
    - ## 概述
    - ### 概述
    - **概述**
    - 【概述】
    """
    lines = markdown.splitlines()
    new_lines = []

    for line in lines:
        stripped = line.strip()

        matched = False
        for title in SECTION_TITLES:
            patterns = [
                rf"^#+\s*{re.escape(title)}\s*$",          # # 概述 / ## 概述
                rf"^\*\*{re.escape(title)}\*\*\s*$",      # **概述**
                rf"^【\s*{re.escape(title)}\s*】\s*$",     # 【概述】
                rf"^{re.escape(title)}\s*$",              # 概述
            ]
            if any(re.match(p, stripped) for p in patterns):
                new_lines.append(f"# {title}")
                matched = True
                break

        if not matched:
            new_lines.append(line)

    markdown = "\n".join(new_lines)

    # 避免标题前后空行混乱
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # 确保一级标题前面有空行（文档第一个标题除外）
    markdown = re.sub(r"([^\n])\n(# )", r"\1\n\n\2", markdown)

    return markdown.strip()


def html_to_markdown(html: str) -> str:
    """HTML 转 Markdown"""
    soup = BeautifulSoup(html, "lxml")
    soup = clean_soup(soup)
    main_node = pick_main_content(soup)

    main_html = str(main_node)

    markdown = md(
        main_html,
        heading_style="ATX",
        bullets="-",
        strip=["span"],
    )

    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()

    # 把指定栏目映射成一级标题
    markdown = normalize_special_headings(markdown)

    title = soup.title.get_text(strip=True) if soup.title else "网页内容"
    markdown = f"# {title}\n\n来源：{URL}\n\n{markdown}\n"
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    return markdown


def main():
    print("1) 正在抓取网页 HTML...")
    html = fetch_html(URL)

    print(f"2) 保存原始 HTML 到: {HTML_OUTPUT}")
    save_text(html, HTML_OUTPUT)

    print("3) 正在转换为 Markdown...")
    markdown = html_to_markdown(html)

    print(f"4) 保存 Markdown 到: {MD_OUTPUT}")
    save_text(markdown, MD_OUTPUT)

    print("完成。")
    print(f"- HTML 文件: {HTML_OUTPUT}")
    print(f"- Markdown 文件: {MD_OUTPUT}")


if __name__ == "__main__":
    main()