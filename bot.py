import asyncio
from pathlib import Path
from playwright.async_api import Page


class BungaeBot:
    BASE = "https://www.bunjang.co.kr"

    CONDITION_MAP = {
        "N":  "새 상품 (미사용)",
        "S":  "사용감 없음",
        "A+": "사용감 없음",
        "A":  "사용감 적음",
        "B":  "사용감 많음",
        "C":  "고장/파손 상품",
    }

    def __init__(self, page: Page, cred: dict, product: dict,
                 price: int, images: list[str], description: str):
        self.page = page
        self.cred = cred
        self.product = product
        self.price = price
        self.images = images
        self.description = description

    # ── 실행 진입점 ─────────────────────────────────────────────────
    async def run(self) -> None:
        await self._go_to_register()
        await self._fill_form()
        await self._submit()

    # ── 등록 페이지 이동 (세션 없으면 로그인) ────────────────────────
    async def _go_to_register(self) -> None:
        await self.page.goto(f"{self.BASE}/products/new", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1500)

        if "/products/new" not in self.page.url:
            print("  세션 없음 → 네이버 로그인")
            await self._naver_login()
            await self.page.goto(f"{self.BASE}/products/new", wait_until="domcontentloaded")
            await self.page.wait_for_timeout(1500)

        print(f"  등록 페이지 이동 완료")

    # ── 네이버 OAuth 로그인 ─────────────────────────────────────────
    async def _naver_login(self) -> None:
        await self.page.goto(f"{self.BASE}/login", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(800)

        try:
            async with self.page.context.expect_page(timeout=4000) as popup_info:
                await self.page.click("button:has-text('네이버로 로그인')")
            naver = await popup_info.value
        except Exception:
            await self.page.wait_for_url("**/nid.naver.com/**", timeout=15000)
            naver = self.page

        await naver.wait_for_load_state("domcontentloaded")
        await naver.fill("input#id", self.cred["naver_id"])
        await naver.fill("input#pw", self.cred["naver_password"])
        await naver.click("button#log\\.login")

        print("  네이버 추가 인증이 필요하면 직접 완료하세요 (최대 3분 대기)...")
        if naver != self.page:
            try:
                await naver.wait_for_event("close", timeout=180000)
            except Exception:
                pass
            await self.page.bring_to_front()
        else:
            try:
                await naver.wait_for_function(
                    "!window.location.href.includes('nid.naver.com')", timeout=180000
                )
            except Exception:
                pass
        await self.page.wait_for_load_state("domcontentloaded")

    # ── 폼 입력 ─────────────────────────────────────────────────────
    async def _fill_form(self) -> None:
        p = self.product
        print("  이미지 업로드...")
        await self.page.wait_for_timeout(1000)
        if self.images:
            await self.page.locator("#media-input").set_input_files(self.images)
            await self.page.wait_for_timeout(2000)

        print("  상품명 입력...")
        title = self.page.locator("input[placeholder='상품명을 입력해 주세요.']")
        await title.wait_for(timeout=10000)
        await title.fill(p["title_ko"])

        print("  카테고리 선택...")
        for label in ["패션잡화", "가방", "숄더"]:
            try:
                item = self.page.locator(f"li:has-text('{label}')").first
                await item.wait_for(timeout=5000)
                await item.click()
                await self.page.wait_for_timeout(500)
            except Exception:
                pass

        print("  가격 입력...")
        price_input = self.page.locator("input[placeholder*='가격']").first
        await price_input.wait_for(timeout=10000)
        await price_input.fill(str(self.price))

        print("  상품 상태 선택...")
        cond_label = self.CONDITION_MAP.get(p["condition"], "사용감 없음")
        trigger = self.page.locator("text=상품 상태를 선택해 주세요").first
        await trigger.wait_for(timeout=10000)
        await trigger.click()
        await self.page.wait_for_timeout(500)
        opt = self.page.locator(f"text={cond_label}").first
        await opt.wait_for(timeout=5000)
        await opt.click()
        await self.page.wait_for_timeout(300)

        print("  설명 입력...")
        # 첫 줄(영문 상품명) 제거, 하단 검색 태그 섹션 분리
        lines = self.description.splitlines()
        body_lines = []
        tag_lines = []
        in_tag_section = False
        for line in lines[1:]:
            if "검색 태그" in line or "검색태그" in line:
                in_tag_section = True
                continue
            if in_tag_section:
                tag_lines.append(line)
            else:
                body_lines.append(line)
        body = "\n".join(body_lines).strip()
        desc = self.page.locator("textarea").first
        await desc.wait_for(timeout=10000)
        await desc.fill(body)
        # 설명 입력 후 IME 완전 종료
        await self.page.keyboard.press("Escape")
        await self.page.wait_for_timeout(400)

        # 검색 태그 입력
        raw_tags = " ".join(tag_lines)
        tags = [t.strip().lstrip("#") for t in raw_tags.replace(",", " ").split() if t.strip()]
        if tags:
            print(f"  태그 입력... ({len(tags)}개)")
            tag_input = self.page.locator("input[placeholder*='태그']").first
            try:
                await tag_input.wait_for(timeout=5000)
                await tag_input.evaluate("el => el.focus()")
                await self.page.wait_for_timeout(400)
                for tag in tags:
                    # 클립보드 경유 붙여넣기 → IME 완전 우회
                    await self.page.evaluate(
                        "t => navigator.clipboard.writeText(t)", tag
                    )
                    await self.page.wait_for_timeout(150)
                    await self.page.keyboard.press("Control+a")
                    await self.page.keyboard.press("Backspace")
                    await self.page.keyboard.press("Control+v")
                    await self.page.wait_for_timeout(300)
                    await self.page.keyboard.press("Enter")
                    await self.page.wait_for_timeout(400)
            except Exception:
                print("  태그 입력 필드를 찾지 못했습니다 — 건너뜀")

    # ── 등록 완료 ────────────────────────────────────────────────────
    async def _submit(self) -> None:
        print("\n  입력 완료. 브라우저에서 내용을 확인하세요.")
        print("  엔터를 누르면 등록하기를 클릭합니다. (중단: Ctrl+C)")
        await asyncio.get_event_loop().run_in_executor(None, input)

        btn = self.page.locator("button:has-text('등록하기')").first
        await btn.wait_for(timeout=10000)
        await btn.click()
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(1500)
        print(f"  등록 완료 ✓ → {self.page.url}")
