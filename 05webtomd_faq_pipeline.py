#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
整合 01 和 04 的处理流程：
1. 抓取网页原始 HTML，保存到 data 目录。
2. 将正文整理为 Markdown，保存到 data 目录。
3. 抽取「患者最常问的问题」FAQ 问答对，保存为 JSON 和 Markdown。
4. 如环境安装了 Playwright，可直接渲染页面获取 FAQ；
   如未安装，也支持传入已保存的 rendered HTML 做离线测试。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag


DEFAULT_URL = (
    "https://www.baidu.com/bh/dict/ydzz_13484531980504204614"
    "?from=dicta&sf_ref=med_pc&sf_ch=ch_med_pc"
)
DEFAULT_OUTPUT_DIR = Path("data")
RAW_HTML_NAME = "baidu_yidian_raw.html"
RENDERED_HTML_NAME = "faq_rendered_snapshot.html"
MARKDOWN_NAME = "baidu_yidian.md"
FAQ_JSON_NAME = "faq_qa.json"
FAQ_MD_NAME = "faq_qa.md"
SECTION_TITLES = ("概述", "原因", "就医", "诊断", "治疗", "日常")

SKIP_TAGS = {"script", "style", "noscript", "iframe", "svg", "form", "button", "input"}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.baidu.com/",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="整合网页转 Markdown 与 FAQ 抽取，输出到 data 目录。"
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="要处理的网页地址。")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="输出目录，默认写入 ./data。",
    )
    parser.add_argument(
        "--source-html",
        help="已保存的原始 HTML 文件路径；提供后将跳过在线抓取。",
    )
    parser.add_argument(
        "--rendered-html",
        help="已保存的渲染后 HTML 文件路径；适合离线测试 FAQ 抽取。",
    )
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="不尝试使用 Playwright 渲染页面。若未提供 --rendered-html，FAQ 可能无法抽取。",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="仅在使用 Playwright 时生效：显示浏览器窗口，便于排查页面渲染问题。",
    )
    return parser.parse_args()


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\xa0", " ").split()).strip()


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_text(content: str, file_path: Path) -> None:
    file_path.write_text(content, encoding="utf-8")


def read_or_fetch_html(url: str, source_html: str | None, output_path: Path) -> str:
    if source_html:
        source_path = Path(source_html)
        html = source_path.read_text(encoding="utf-8")
        if source_path.resolve() != output_path.resolve():
            shutil.copyfile(source_path, output_path)
        return html

    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "缺少 requests，无法在线抓取页面；请安装 requests，或使用 --source-html 传入本地 HTML。"
        ) from exc

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding

    html = response.text
    save_text(html, output_path)
    return html


def render_html_with_playwright(url: str, headless: bool) -> str:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except ImportError as exc:
        raise RuntimeError(
            "缺少 Playwright，无法在线渲染 FAQ。请安装 playwright，"
            "或使用 --rendered-html 传入已保存的渲染后 HTML。"
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="zh-CN",
            viewport={"width": 1600, "height": 2400},
        )
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        try:
            page.wait_for_selector("#richTextContainer", timeout=15000)
        except PlaywrightTimeoutError:
            pass

        for _ in range(3):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(300)

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1500)

        html = page.content()
        browser.close()
        return html


def read_or_render_html(
    url: str,
    rendered_html: str | None,
    output_path: Path,
    skip_render: bool,
    show_browser: bool,
) -> str | None:
    if rendered_html:
        source_path = Path(rendered_html)
        html = source_path.read_text(encoding="utf-8")
        if source_path.resolve() != output_path.resolve():
            shutil.copyfile(source_path, output_path)
        return html

    if skip_render:
        return None

    html = render_html_with_playwright(url=url, headless=not show_browser)
    save_text(html, output_path)
    return html


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    for tag in soup.find_all(SKIP_TAGS):
        tag.decompose()
    return soup


def pick_main_content(soup: BeautifulSoup) -> Tag:
    rich_text = soup.find(id="richTextContainer")
    if isinstance(rich_text, Tag):
        return rich_text

    candidates = [
        {"id": re.compile(r"(content|main|article|detail|lemma)", re.I)},
        {"class_": re.compile(r"(content|main|article|detail|lemma|body)", re.I)},
        {"attrs": {"role": "main"}},
    ]

    for rule in candidates:
        node = soup.find(**rule)
        if isinstance(node, Tag) and len(node.get_text(strip=True)) > 200:
            return node

    if isinstance(soup.body, Tag):
        return soup.body
    return soup


def normalize_markdown(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = text.strip()

    for title in SECTION_TITLES:
        text = re.sub(rf"(?m)^#+\s*{re.escape(title)}\s*$", f"# {title}", text)
        text = re.sub(rf"(?m)^\*\*{re.escape(title)}\*\*\s*$", f"# {title}", text)
        text = re.sub(rf"(?m)^【\s*{re.escape(title)}\s*】\s*$", f"# {title}", text)
        text = re.sub(rf"(?m)^{re.escape(title)}\s*$", f"# {title}", text)

    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def get_tag_list(parent: Tag, name: str, recursive: bool = False) -> list[Tag]:
    return [tag for tag in parent.find_all(name, recursive=recursive) if isinstance(tag, Tag)]


def section_to_markdown(section: Tag) -> list[str]:
    lines: list[str] = []

    title_node = section.find("div", class_="health-dict__overview__text__level1-tag__title")
    section_title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
    if section_title:
        lines.append(f"# {section_title}")
        lines.append("")

    summary_items = [
        clean_text(item.get_text(" ", strip=True))
        for item in section.select("ul.health-dict__overview__text__level1-tag__texts > li")
    ]
    summary_items = [item for item in summary_items if item]
    for item in summary_items:
        lines.append(f"- {item}")
    if summary_items:
        lines.append("")

    html_container = section.find("div", class_="health-dict__html")
    if isinstance(html_container, Tag):
        body_root = html_container.find("div")
        if isinstance(body_root, Tag):
            lines.extend(render_container(body_root))

    return lines


def render_container(node: Tag) -> list[str]:
    lines: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = clean_text(str(child))
            if text:
                lines.append(text)
                lines.append("")
            continue
        if not isinstance(child, Tag) or child.name in SKIP_TAGS:
            continue
        lines.extend(render_block(child))
    return lines


def render_block(node: Tag) -> list[str]:
    if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = min(int(node.name[1]), 6)
        text = clean_text(node.get_text(" ", strip=True))
        return [f"{'#' * level} {text}", ""] if text else []

    if node.name == "img":
        src = clean_text(node.get("src", ""))
        return [f"![]({src})", ""] if src else []

    if node.name in {"ul", "ol"}:
        lines: list[str] = []
        ordered = node.name == "ol"
        items = get_tag_list(node, "li", recursive=False)
        for index, item in enumerate(items, start=1):
            text = clean_text(item.get_text(" ", strip=True))
            if not text:
                continue
            marker = f"{index}." if ordered else "-"
            lines.append(f"{marker} {text}")
        if lines:
            lines.append("")
        return lines

    if node.name == "p":
        return render_paragraph(node)

    child_tags = [child for child in node.children if isinstance(child, Tag) and child.name not in SKIP_TAGS]
    if child_tags:
        lines: list[str] = []
        for child in child_tags:
            lines.extend(render_block(child))
        if lines:
            return lines

    text = clean_text(node.get_text(" ", strip=True))
    return [text, ""] if text else []


def render_paragraph(node: Tag) -> list[str]:
    lines: list[str] = []
    text_parts: list[str] = []

    for child in node.children:
        if isinstance(child, NavigableString):
            text_parts.append(str(child))
            continue

        if not isinstance(child, Tag) or child.name in SKIP_TAGS:
            continue

        if child.name == "img":
            paragraph = clean_text(" ".join(text_parts))
            if paragraph:
                lines.append(paragraph)
                lines.append("")
                text_parts.clear()

            src = clean_text(child.get("src", ""))
            if src:
                lines.append(f"![]({src})")
                lines.append("")
            continue

        if child.name == "br":
            text_parts.append("\n")
            continue

        text_parts.append(child.get_text(" ", strip=True))

    paragraph = clean_text(" ".join(text_parts))
    if paragraph:
        lines.append(paragraph)
        lines.append("")
    return lines


def generic_to_markdown(main_node: Tag) -> str:
    lines: list[str] = []
    for child in main_node.children:
        if not isinstance(child, Tag) or child.name in SKIP_TAGS:
            continue
        lines.extend(render_block(child))
    return normalize_markdown("\n".join(lines))


def html_to_markdown(html: str, url: str) -> str:
    soup = clean_soup(BeautifulSoup(html, "html.parser"))
    main_node = pick_main_content(soup)

    title = soup.title.get_text(strip=True) if soup.title else "网页内容"
    lines = [f"# {title}", "", f"来源: {url}", ""]

    if main_node.get("id") == "richTextContainer":
        sections = main_node.find_all("div", class_="health-dict__overview__text", recursive=False)
        if sections:
            for section in sections:
                lines.extend(section_to_markdown(section))
            return normalize_markdown("\n".join(lines))

    lines.append(generic_to_markdown(main_node).strip())
    return normalize_markdown("\n".join(lines))


def extract_faq_from_html(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    question_blocks = soup.find_all(
        "div",
        class_="health-dict__overview__text__level1-tag__questions__question",
    )

    results: list[dict[str, str]] = []
    seen_questions: set[str] = set()
    for block in question_blocks:
        title_node = block.find(
            "div",
            class_="health-dict__overview__text__level1-tag__questions__question__title",
        )
        content_node = block.find(
            "div",
            class_="health-dict__overview__text__level1-tag__questions__question__content",
        )

        question = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
        answer = clean_text(content_node.get_text(" ", strip=True)) if content_node else ""
        if question and answer and question not in seen_questions:
            seen_questions.add(question)
            results.append({"question": question, "answer": answer})

    return results


def faq_to_markdown(items: Iterable[dict[str, str]], url: str) -> str:
    lines = ["# 患者最常问的问题", "", f"来源: {url}", ""]
    for item in items:
        lines.append(f"## {item['question']}")
        lines.append("")
        lines.append(item["answer"])
        lines.append("")
    return normalize_markdown("\n".join(lines))


def main() -> None:
    args = parse_args()
    output_dir = ensure_output_dir(Path(args.output_dir))

    raw_html_path = output_dir / RAW_HTML_NAME
    rendered_html_path = output_dir / RENDERED_HTML_NAME
    markdown_path = output_dir / MARKDOWN_NAME
    faq_json_path = output_dir / FAQ_JSON_NAME
    faq_md_path = output_dir / FAQ_MD_NAME

    print("1) 处理原始 HTML...")
    raw_html = read_or_fetch_html(
        url=args.url,
        source_html=args.source_html,
        output_path=raw_html_path,
    )

    print("2) 生成网页 Markdown...")
    markdown = html_to_markdown(raw_html, url=args.url)
    save_text(markdown, markdown_path)

    print("3) 处理 FAQ 渲染页...")
    rendered_html = read_or_render_html(
        url=args.url,
        rendered_html=args.rendered_html,
        output_path=rendered_html_path,
        skip_render=args.skip_render,
        show_browser=args.show_browser,
    )

    faq_source_html = rendered_html if rendered_html else raw_html
    faq_items = extract_faq_from_html(faq_source_html)

    if not faq_items:
        if rendered_html is None:
            raise RuntimeError(
                "未抽取到 FAQ。当前运行没有可用的 rendered HTML，"
                "请安装 Playwright 后直接运行，或使用 --rendered-html 传入已保存的渲染页。"
            )
        raise RuntimeError("已读取 rendered HTML，但仍未抽取到 FAQ，请检查页面结构是否变化。")

    print("4) 保存 FAQ 结果...")
    faq_json_path.write_text(
        json.dumps(faq_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    faq_md_path.write_text(
        faq_to_markdown(faq_items, url=args.url),
        encoding="utf-8",
    )

    print("完成。")
    print(f"- 原始 HTML: {raw_html_path}")
    print(f"- 网页 Markdown: {markdown_path}")
    print(f"- 渲染 HTML: {rendered_html_path if rendered_html else '未生成'}")
    print(f"- FAQ JSON: {faq_json_path}")
    print(f"- FAQ Markdown: {faq_md_path}")
    print(f"- FAQ 数量: {len(faq_items)}")


if __name__ == "__main__":
    main()
