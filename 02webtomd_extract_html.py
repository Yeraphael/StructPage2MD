# -*- coding: utf-8 -*-
"""
只做一件事：
打开百度页面，等待渲染完成后，保存当前页面 DOM 到 faq_rendered_snapshot.html
"""

from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://www.baidu.com/bh/dict/ydzz_10913524287527321158?from=dicta&sf_ref=med_pc&sf_ch=ch_med_pc"
OUTPUT_HTML = "faq_rendered_snapshot.html"


def save_rendered_html(url: str, output_file: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 调试时建议 False，确认稳定后可改成 True
            args=["--disable-blink-features=AutomationControlled"]
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

        # 尝试等待正文区域
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


if __name__ == "__main__":
    save_rendered_html(URL, OUTPUT_HTML)