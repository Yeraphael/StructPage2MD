#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名: 03extract_faq.py
作者: Yeraphael
项目: webTomd
创建日期: 2026/4/12
描述:
"""
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from bs4 import BeautifulSoup


HTML_FILE = "faq_rendered_snapshot.html"
JSON_OUTPUT = "faq_qa.json"
MD_OUTPUT = "faq_qa.md"


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.replace("\xa0", " ").split()).strip()


def extract_faq_from_html(html_path: str):
    html = Path(html_path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # 找 FAQ 栏目标题
    title_nodes = soup.find_all(
        "div",
        class_="health-dict__overview__text__level1-tag__questions__title"
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
        class_="health-dict__overview__text__level1-tag__questions__question"
    )

    results = []

    for block in question_blocks:
        q_el = block.find(
            "div",
            class_="health-dict__overview__text__level1-tag__questions__question__title"
        )
        a_el = block.find(
            "div",
            class_="health-dict__overview__text__level1-tag__questions__question__content"
        )

        question = clean_text(q_el.get_text(" ", strip=True)) if q_el else ""
        answer = clean_text(a_el.get_text(" ", strip=True)) if a_el else ""

        if question and answer:
            results.append({
                "question": question,
                "answer": answer
            })

    return results


def build_markdown(items):
    lines = ["# 患者最常问的问题", ""]
    for item in items:
        lines.append(f"## {item['question']}")
        lines.append("")
        lines.append(item["answer"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main():
    items = extract_faq_from_html(HTML_FILE)
    print("提取到问答对数量:", len(items))

    if not items:
        raise ValueError("HTML 中仍未提取到 FAQ 问答对，请检查类名是否变化。")

    Path(JSON_OUTPUT).write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    Path(MD_OUTPUT).write_text(build_markdown(items), encoding="utf-8")

    print("已保存:", JSON_OUTPUT)
    print("已保存:", MD_OUTPUT)


if __name__ == "__main__":
    main()