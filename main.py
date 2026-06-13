"""
luxury-bot: 명품 상품을 여러 플랫폼에 자동 등록하는 스크립트

사용법:
  python main.py                          # 전체 6개 플랫폼 실행
  python main.py --platforms guugus bungae  # 특정 플랫폼만
  python main.py --images img1.jpg img2.jpg # 이미지 경로 직접 지정
  python main.py --dry-run               # 실제 등록 없이 로그인까지만 테스트
"""

import asyncio
import argparse
import subprocess
import sys
import time
import os
from pathlib import Path

import yaml
from playwright.async_api import async_playwright, Browser, BrowserContext

sys.path.insert(0, str(Path(__file__).parent))
from platforms.guugus import Guugus
from platforms.feelway import Feelway
from platforms.trenbe import Trenbe
from platforms.rebonz import Rebonz
from platforms.mustit import Mustit
from platforms.bungae import Bungae

PLATFORM_MAP = {
    "guugus": Guugus,
    "feelway": Feelway,
    "trenbe": Trenbe,
    "rebonz": Rebonz,
    "mustit": Mustit,
    "bungae": Bungae,
}

ROOT = Path(__file__).parent


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ask_images() -> list[str]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(title="이미지 폴더를 선택하세요")
    root.destroy()

    if not folder:
        return []

    # 1.jpg ~ 10.jpg 순서대로 수집
    images = []
    for i in range(1, 11):
        for ext in ("jpg", "jpeg", "JPG", "JPEG", "png", "PNG"):
            p = Path(folder) / f"{i}.{ext}"
            if p.exists():
                images.append(str(p))
                break

    if not images:
        print(f"  ✗ 선택한 폴더에 이미지가 없습니다: {folder}")
    else:
        print(f"  이미지 {len(images)}장 선택됨: {folder}")
        for img in images:
            print(f"    - {Path(img).name}")

    # product.txt가 있으면 상품 설명으로 사용
    txt_path = Path(folder) / "product.txt"
    if txt_path.exists():
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                desc = txt_path.read_text(encoding=enc).strip()
                break
            except UnicodeDecodeError:
                continue
        else:
            desc = ""
        print(f"  product.txt 로드됨 ({len(desc)}자)")
        return images, desc

    return images, None


async def run_platform(browser: Browser, platform_key: str, creds: dict,
                       product: dict, price: int, images: list[str],
                       description: str | None, dry_run: bool) -> tuple[str, bool, str]:
    cls = PLATFORM_MAP[platform_key]
    # Whale의 기존 컨텍스트(로그인 세션·쿠키 포함)를 재사용
    if browser.contexts:
        context = browser.contexts[0]
    else:
        context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    await page.evaluate("() => { window.moveTo(0,0); window.resizeTo(screen.availWidth, screen.availHeight); }")
    instance = cls(page, creds[platform_key], product, price, images, description)

    try:
        if dry_run:
            await instance.login()
            print(f"  [{instance.name}] 로그인 테스트 완료 (dry-run)")
        else:
            await instance.run()
        return (platform_key, True, "")
    except Exception as e:
        msg = str(e)
        print(f"  [{instance.name}] ✗ 오류 발생: {msg}")
        await page.screenshot(path=str(ROOT / f"error_{platform_key}.png"))
        return (platform_key, False, msg)
    finally:
        await page.close()  # 탭만 닫고 컨텍스트(세션)는 유지


async def main() -> None:
    parser = argparse.ArgumentParser(description="명품 상품 자동 등록 봇")
    parser.add_argument("--platforms", nargs="+", choices=list(PLATFORM_MAP.keys()),
                        default=list(PLATFORM_MAP.keys()), help="실행할 플랫폼 (기본: 전체)")
    parser.add_argument("--images", nargs="+", help="이미지 파일 경로들")
    parser.add_argument("--dry-run", action="store_true", help="로그인까지만 테스트")
    parser.add_argument("--headless", action="store_true", help="브라우저 창 숨기기")
    args = parser.parse_args()

    # 설정 파일 로드
    product_cfg = load_yaml(ROOT / "product.yaml")["product"]
    prices_cfg = load_yaml(ROOT / "product.yaml")["prices"]
    creds = load_yaml(ROOT / "credentials.yaml")

    # 이미지 경로 및 설명 결정
    description: str | None = None
    images: list[str] = args.images or []
    if not images and not args.dry_run:
        images, description = ask_images()
        if not images:
            print("이미지가 없으면 등록이 불완전할 수 있습니다. 계속하시겠습니까? (y/n): ", end="")
            if input().strip().lower() != "y":
                sys.exit(0)

    print(f"\n등록 상품: {product_cfg['title_ko']}")
    print(f"대상 플랫폼: {', '.join(args.platforms)}")
    if args.dry_run:
        print("모드: DRY-RUN (로그인 테스트만)")

    results: list[tuple[str, bool, str]] = []

    whale_path = r"C:\Program Files\Naver\Naver Whale\Application\whale.exe"
    whale_profile = Path(os.environ["LOCALAPPDATA"]) / "Naver" / "Naver Whale" / "User Data"
    cdp_port = 9222
    whale_proc = subprocess.Popen([
        whale_path,
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={whale_profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "about:blank",
    ])
    time.sleep(2)  # Whale 기동 대기

    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(f"http://localhost:{cdp_port}", slow_mo=200)

        # 플랫폼을 순차 실행 (각 사이트마다 로그인 세션이 독립적)
        for key in args.platforms:
            result = await run_platform(
                browser, key, creds, product_cfg,
                prices_cfg[key], images, description, args.dry_run
            )
            results.append(result)

        await browser.close()

    whale_proc.terminate()

    # 결과 요약
    print(f"\n{'='*50}")
    print("  최종 결과 요약")
    print(f"{'='*50}")
    for key, success, err in results:
        status = "✓ 성공" if success else f"✗ 실패: {err[:60]}"
        print(f"  {PLATFORM_MAP[key].name:<10} {status}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
