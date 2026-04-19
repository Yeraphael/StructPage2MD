#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件名: webtomd_faq_all_in_one.py

功能：
1. 打开百度医典页面，等待渲染完成后保存当前 DOM 到 faq_rendered_snapshot.html
2. 从 faq_rendered_snapshot.html 中提取【患者最常问的问题】栏目下的问答对
3. 输出 faq_qa.json 和 faq_qa.md

安装依赖：
    pip install playwright beautifulsoup4 lxml
    playwright install
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


URL = "https://www.baidu.com/bh/dict/ydzz_13484531980504204614?from=dicta&sf_ref=med_pc&sf_ch=ch_med_pc"

HTML_OUTPUT = "faq_rendered_snapshot1.html"
JSON_OUTPUT = "faq_qa1.json"
MD_OUTPUT = "faq_qa1.md"


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\xa0", " ").split()).strip()


def save_rendered_html(url: str, output_file: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 调试阶段建议 False；稳定后可改 True
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            viewport={"width": 1600, "height": 2400},
        )

        page = context.new_page()

        print("1) 打开页面...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("2) 等待首屏渲染...")
        page.wait_for_timeout(4000)

        try:
            page.wait_for_selector("#richTextContainer", timeout=15000)
            print("3) 检测到 #richTextContainer")
        except PlaywrightTimeoutError:
            print("3) 未等到 #richTextContainer，继续执行滚动抓取")

        print("4) 向下滚动，触发懒加载...")
        for i in range(3):
            page.mouse.wheel(0, 2200)
            page.wait_for_timeout(300)
            print(f"   - 第 {i + 1} 次滚动完成")

        print("5) 回到顶部...")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1500)

        print("6) 保存渲染后的 HTML...")
        html = page.content()
        Path(output_file).write_text(html, encoding="utf-8")

        print(f"完成，已保存到: {output_file}")
        print("HTML 长度:", len(html))
        print("是否包含 richTextContainer:", "richTextContainer" in html)
        print("是否包含 患者最常问的问题:", "患者最常问的问题" in html)

        browser.close()


def extract_faq_from_html(html_path: str):
    html = Path(html_path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # 找 FAQ 栏目标题
    title_nodes = soup.find_all(
        "div",
        class_="health-dict__overview__text__level1-tag__questions__title",
    )

    section_root = None
    for node in title_nodes:
        if clean_text(node.get_text()) == "患者最常问的问题":
            parent = node.parent
            while parent:
                classes = parent.get("class", [])
                if "health-dict__overview__text__level1-tag__questions" in classes:
                    section_root = parent
                    break
                parent = parent.parent
            if section_root:
                break

    if not section_root:
        return []

    question_blocks = section_root.find_all(
        "div",
        class_="health-dict__overview__text__level1-tag__questions__question",
    )

    results = []

    for block in question_blocks:
        q_el = block.find(
            "div",
            class_="health-dict__overview__text__level1-tag__questions__question__title",
        )
        a_el = block.find(
            "div",
            class_="health-dict__overview__text__level1-tag__questions__question__content",
        )

        question = clean_text(q_el.get_text(" ", strip=True)) if q_el else ""
        answer = clean_text(a_el.get_text(" ", strip=True)) if a_el else ""

        if question and answer:
            results.append(
                {
                    "question": question,
                    "answer": answer,
                }
            )

    return results


def build_markdown(items):
    lines = ["# 患者最常问的问题", ""]
    for item in items:
        lines.append(f"## {item['question']}")
        lines.append("")
        lines.append(item["answer"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def save_faq_outputs(items, json_output: str, md_output: str) -> None:
    Path(json_output).write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path(md_output).write_text(build_markdown(items), encoding="utf-8")

    print("已保存:", json_output)
    print("已保存:", md_output)


def main():
    save_rendered_html(URL, HTML_OUTPUT)

    print("7) 从渲染后的 HTML 中提取 FAQ...")
    items = extract_faq_from_html(HTML_OUTPUT)
    print("提取到问答对数量:", len(items))

    if not items:
        raise ValueError(
            "HTML 中未提取到 FAQ 问答对，请检查：\n"
            "1. faq_rendered_snapshot.html 里是否包含“患者最常问的问题”\n"
            "2. 相关类名是否发生变化\n"
            "3. 是否需要增加滚动次数和等待时间"
        )

    print("8) 保存 JSON 和 Markdown...")
    save_faq_outputs(items, JSON_OUTPUT, MD_OUTPUT)

    print("全部完成。")


if __name__ == "__main__":
    main()