from base_platform import BasePlatform


class Guugus(BasePlatform):
    name = "구구스"
    BASE = "https://www.guugus.com"

    async def login(self) -> None:
        await self.page.goto(f"{self.BASE}/member/login")
        await self.page.wait_for_load_state("domcontentloaded")

        # 구구스 ID/PW 입력
        await self.fill("input[name='id']", self.cred["id"])
        await self.fill("input[name='password']", self.cred["password"])
        await self.click("button[type='submit']")
        await self.page.wait_for_load_state("domcontentloaded")

        # 구글 2차 인증 페이지가 뜨는 경우 수동 완료 대기 (최대 120초)
        if "google.com" in self.page.url or "accounts.google" in self.page.url:
            print(f"  [{self.name}] 구글 2차 인증을 직접 완료해 주세요 (120초 대기)...")
            await self.page.wait_for_function(
                "!window.location.href.includes('google.com')", timeout=120000
            )
            await self.page.wait_for_load_state("domcontentloaded")

    async def navigate_to_register(self) -> None:
        await self.page.goto(f"{self.BASE}/product/write")
        await self.page.wait_for_load_state("domcontentloaded")

    async def fill_form(self) -> None:
        p = self.product

        # 이미지
        await self.upload_images("input[type='file']")

        # 상품명
        await self.fill("input[name='subject']", p["title_ko"])

        # 브랜드 (드롭다운 또는 텍스트)
        await self.fill("input[name='brand']", p["brand"])

        # 품번
        await self.fill("input[name='model_no']", p["model_number"])

        # 카테고리 — 직접 클릭으로 선택
        # (실제 셀렉터는 사이트 확인 후 수정)
        await self.click("text=가방")
        await self.click("text=크로스백")

        # 컨디션
        await self.click(f"label:has-text('{p['condition']} 등급')")

        # 가격
        await self.fill("input[name='price']", str(self.price))

        # 상세 설명
        await self.fill("textarea[name='content']", p["description"])

        # 구성품
        await self.fill("textarea[name='accessories']", self.accessories_text())

    async def submit(self) -> None:
        await self.click("button:has-text('등록')")
        await self.page.wait_for_load_state("domcontentloaded")
