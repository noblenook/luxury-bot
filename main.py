"""
번개장터 상품 자동 등록 봇

사용법:
  python main.py            # 폴더 선택 창 → 자동 등록
  python main.py --dry-run  # 등록 페이지 진입까지만 테스트
"""

import asyncio
import subprocess
import sys
import time
import os
from pathlib import Path

import yaml
from playwright.async_api import async_playwright

from bot import BungaeBot

ROOT = Path(__file__).parent
WHALE = r"C:\Program Files\Naver\Naver Whale\Application\whale.exe"
WHALE_PROFILE = Path(os.environ["LOCALAPPDATA"]) / "Naver" / "Naver Whale" / "User Data"
CDP_PORT = 9222


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_folder() -> tuple[list[str], str]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    folder = filedialog.askdirectory(title="이미지 폴더를 선택하세요")
    root.destroy()

    if not folder:
        print("폴더를 선택하지 않았습니다.")
        sys.exit(0)

    # 1.jpg ~ 10.jpg 순서 수집
    images = []
    for i in range(1, 11):
        for ext in ("jpg", "jpeg", "JPG", "JPEG", "png", "PNG"):
            p = Path(folder) / f"{i}.{ext}"
            if p.exists():
                images.append(str(p))
                break

    if not images:
        print(f"이미지를 찾을 수 없습니다: {folder}")
        sys.exit(0)

    print(f"이미지 {len(images)}장: {folder}")

    # product.txt 로드
    txt = Path(folder) / "product.txt"
    description = ""
    if txt.exists():
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                description = txt.read_text(encoding=enc).strip()
                print(f"product.txt 로드됨 ({len(description)}자)")
                break
            except UnicodeDecodeError:
                continue
    else:
        print("product.txt 없음 — product.yaml의 description 사용")

    return images, description


async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="등록 페이지 진입까지만 테스트")
    args = parser.parse_args()

    cfg = load_yaml(ROOT / "product.yaml")
    product = cfg["product"]
    price = cfg["prices"]["bungae"]
    cred = load_yaml(ROOT / "credentials.yaml")["bungae"]

    images, description = pick_folder()
    if not description:
        description = product.get("description", "")

    print(f"\n상품: {product['title_ko']}")
    print(f"가격: {price:,}원")
    print(f"컨디션: {product['condition']}등급")

    # Whale 실행
    whale_proc = subprocess.Popen([
        WHALE, f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={WHALE_PROFILE}",
        "--no-first-run", "--no-default-browser-check",
        "--start-maximized", "about:blank",
    ])
    time.sleep(2)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(
                f"http://localhost:{CDP_PORT}", slow_mo=150
            )
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.evaluate("() => window.resizeTo(screen.availWidth, screen.availHeight)")

            bot = BungaeBot(page, cred, product, price, images, description)

            if args.dry_run:
                await bot._go_to_register()
                print("dry-run 완료 — 등록은 하지 않습니다.")
            else:
                await bot.run()

            await page.close()
            await browser.close()
    except Exception as e:
        print(f"\n오류 발생: {e}")
    finally:
        whale_proc.terminate()


if __name__ == "__main__":
    asyncio.run(main())
