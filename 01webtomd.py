# -*- coding: utf-8 -*-
"""
将网页抓取为 HTML，并转换成 Markdown 文件
适用于你给的百度医典页面，也可复用到多数普通网页

安装依赖：
    pip install requests beautifulsoup4 markdownify lxml
"""

import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


URL = "https://www.baidu.com/bh/dict/ydzz_10810716394081235114?from=dicta&sf_ref=med_pc&sf_ch=ch_med_pc"
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


def fetch_html(url: str) -> str:
    """抓取网页 HTML"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    # 尽量修正编码，避免中文乱码
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding

    return resp.text


def save_text(content: str, file_path: str) -> None:
    """保存文本到文件"""
    Path(file_path).write_text(content, encoding="utf-8")


def pick_main_content(soup: BeautifulSoup):
    """
    尽量选正文区域。
    没找到就退回 body。
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


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """清理无关标签"""
    for tag in soup([
        "script", "style", "noscript", "iframe", "svg",
        "form", "button", "input", "footer", "nav"
    ]):
        tag.decompose()

    # 去掉常见广告/无用区域
    for tag in soup.find_all(
        attrs={
            "class": re.compile(r"(advert|ad-|ads|nav|footer|toolbar|recommend)", re.I)
        }
    ):
        try:
            tag.decompose()
        except Exception:
            pass

    return soup


def html_to_markdown(html: str) -> str:
    """将 HTML 转成 Markdown"""
    soup = BeautifulSoup(html, "lxml")
    soup = clean_soup(soup)
    main_node = pick_main_content(soup)

    # 转成字符串后再 markdownify
    main_html = str(main_node)

    markdown = md(
        main_html,
        heading_style="ATX",   # # ## ### 风格标题
        bullets="-",
        strip=["span"],        # 去掉无意义 span
    )

    # 简单清洗 Markdown
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = markdown.strip()

    title = soup.title.get_text(strip=True) if soup.title else "网页内容"
    markdown = f"# {title}\n\n来源：{URL}\n\n{markdown}\n"
    return markdown


def main():
    print("1) 正在抓取网页 HTML ...")
    html = fetch_html(URL)

    print(f"2) 保存原始 HTML 到: {HTML_OUTPUT}")
    save_text(html, HTML_OUTPUT)

    print("3) 正在转换为 Markdown ...")
    markdown = html_to_markdown(html)

    print(f"4) 保存 Markdown 到: {MD_OUTPUT}")
    save_text(markdown, MD_OUTPUT)

    print("完成。")
    print(f"- HTML 文件: {HTML_OUTPUT}")
    print(f"- Markdown 文件: {MD_OUTPUT}")


if __name__ == "__main__":
    main()
