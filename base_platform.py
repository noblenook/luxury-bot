from abc import ABC, abstractmethod
from pathlib import Path
from playwright.async_api import Page


class BasePlatform(ABC):
    name: str = ""

    def __init__(self, page: Page, credentials: dict, product: dict, price: int,
                 images: list[str], description: str | None = None):
        self.page = page
        self.cred = credentials
        self.product = product
        self.price = price
        self.images = images
        self.description = description  # product.txt 내용 (없으면 None)

    @abstractmethod
    async def login(self) -> None: ...

    @abstractmethod
    async def navigate_to_register(self) -> None: ...

    @abstractmethod
    async def fill_form(self) -> None: ...

    @abstractmethod
    async def submit(self) -> None: ...

    async def run(self) -> None:
        print(f"\n{'='*50}")
        print(f"  [{self.name}] 시작")
        print(f"{'='*50}")
        await self.login()
        print(f"  [{self.name}] 로그인 완료")
        await self.navigate_to_register()
        print(f"  [{self.name}] 등록 페이지 이동 완료")
        await self.fill_form()
        print(f"  [{self.name}] 폼 입력 완료")
        await self.submit()
        print(f"  [{self.name}] 등록 완료 ✓")

    # 공통 헬퍼 -------------------------------------------------------
    async def fill(self, selector: str, value: str) -> None:
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.fill(selector, value)

    async def click(self, selector: str) -> None:
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.click(selector)

    async def upload_images(self, input_selector: str) -> None:
        if not self.images:
            return
        await self.page.wait_for_selector(input_selector, timeout=10000)
        await self.page.set_input_files(input_selector, self.images)

    async def screenshot(self, filename: str) -> None:
        path = str(Path(__file__).parent / filename)
        await self.page.screenshot(path=path)
        print(f"  [{self.name}] 스크린샷 저장: {filename}")

    async def _find_naver_oauth_button(self) -> str | None:
        """navercorp.com(회사 홈)이 아닌 실제 OAuth 버튼 셀렉터를 반환"""
        # href 기반: nid.naver.com 또는 oauth 경로를 포함한 링크만 허용
        oauth_href_selectors = [
            "a[href*='nid.naver.com']",
            "a[href*='oauth.naver']",
            "a[href*='naver_oauth']",
            "a[href*='naverLogin']",
        ]
        for sel in oauth_href_selectors:
            try:
                await self.page.wait_for_selector(sel, timeout=2000)
                return sel
            except Exception:
                continue

        # 클래스/id 기반 버튼
        class_selectors = [
            ".naver-login", "#naver-login",
            "[class*='naver'][class*='login']",
            "[class*='NaverLogin']",
            "button[class*='naver']",
        ]
        for sel in class_selectors:
            try:
                await self.page.wait_for_selector(sel, timeout=2000)
                return sel
            except Exception:
                continue

        # 텍스트 기반 — navercorp.com으로 가는 링크 제외
        text_candidates = ["a:has-text('네이버 로그인')", "button:has-text('네이버 로그인')",
                           "a:has-text('네이버로 로그인')", "button:has-text('네이버로 로그인')"]
        for sel in text_candidates:
            try:
                el = self.page.locator(sel).first
                href = await el.get_attribute("href") or ""
                if "navercorp.com" not in href:
                    await el.wait_for(timeout=2000)
                    return sel
            except Exception:
                continue

        return None

    async def login_with_naver(self, trigger_selector: str | None = None) -> None:
        """네이버 OAuth 공통 로그인 흐름"""
        # 클릭 전 현재 로그인 페이지 스크린샷 저장 (디버깅용)
        await self.screenshot(f"debug_{self.name}_before_naver_click.png")

        if trigger_selector is None:
            trigger_selector = await self._find_naver_oauth_button()

        if trigger_selector is None:
            raise RuntimeError(
                "네이버 OAuth 버튼을 찾지 못했습니다. "
                f"debug_{self.name}_before_naver_click.png 를 확인하고 "
                "trigger_selector 를 직접 지정하세요."
            )

        print(f"  [{self.name}] 네이버 버튼 클릭: {trigger_selector}")

        # 클릭 후 팝업 또는 같은 탭 이동 모두 처리
        before_url = self.page.url
        naver_page = self.page

        try:
            async with self.page.context.expect_page(timeout=4000) as popup_info:
                await self.page.click(trigger_selector)
            naver_page = await popup_info.value
            print(f"  [{self.name}] 팝업 창에서 네이버 로그인 진행")
        except Exception:
            # 팝업 없음 → 같은 탭에서 이동
            await self.page.wait_for_url("**/nid.naver.com/**", timeout=15000)

        await naver_page.wait_for_load_state("domcontentloaded")

        await naver_page.fill("input#id", self.cred["naver_id"])
        await naver_page.fill("input#pw", self.cred["naver_password"])
        await naver_page.click("button#log\\.login")

        print(f"  [{self.name}] 네이버 추가 인증이 필요하면 브라우저에서 직접 완료하세요 (최대 3분)...")

        if naver_page != self.page:
            # 팝업 방식: 인증 완료 후 팝업이 자동으로 닫힘
            try:
                await naver_page.wait_for_event("close", timeout=180000)
            except Exception:
                pass  # 이미 닫혔거나 타임아웃 — 계속 진행
            # 원래 페이지가 로그인 완료 상태인지 확인
            await self.page.bring_to_front()
            await self.page.wait_for_load_state("domcontentloaded")
        else:
            # 같은 탭 방식: nid.naver.com을 벗어날 때까지 대기
            try:
                await naver_page.wait_for_function(
                    "!window.location.href.includes('nid.naver.com')", timeout=180000
                )
                await naver_page.wait_for_load_state("domcontentloaded")
            except Exception:
                pass

    async def select_option_by_text(self, selector: str, text: str) -> None:
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.select_option(selector, label=text)

    def accessories_text(self) -> str:
        """구성품 목록을 텍스트로 반환"""
        mapping = {
            "guarantee_card": "정품보증서",
            "box": "정품박스",
            "case": "케이스",
            "dust_bag": "더스트백",
            "invoice": "인보이스",
            "receipt": "카드영수증",
            "booklet": "북렛",
            "tag": "택",
        }
        acc = self.product.get("accessories", {})
        return ", ".join(v for k, v in mapping.items() if acc.get(k))
