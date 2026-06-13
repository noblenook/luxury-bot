from base_platform import BasePlatform


class Trenbe(BasePlatform):
    name = "트렌비"
    BASE = "https://www.trenbe.com"

    async def login(self) -> None:
        await self.page.goto(f"{self.BASE}/login")
        await self.fill("input[name='email']", self.cred["id"])
        await self.fill("input[name='password']", self.cred["password"])
        await self.click("button[type='submit']")
        await self.page.wait_for_load_state("domcontentloaded")

    async def navigate_to_register(self) -> None:
        # 트렌비 셀러 센터 → 상품 등록
        await self.page.goto(f"{self.BASE}/seller/product/new")
        await self.page.wait_for_load_state("domcontentloaded")

    async def fill_form(self) -> None:
        p = self.product

        # 브랜드 검색 선택
        await self.fill("input[placeholder*='브랜드']", p["brand"])
        await self.page.wait_for_selector(".brand-dropdown-item", timeout=5000)
        await self.click(".brand-dropdown-item:first-child")

        # 카테고리
        await self.click("text=가방")
        await self.click("text=숄더/크로스백")

        # 상품명
        await self.fill("input[name='name']", p["title_ko"])

        # 모델번호
        await self.fill("input[name='modelNo']", p["model_number"])

        # 색상
        await self.fill("input[name='color']", p["color"])

        # 소재
        await self.fill("input[name='material']", p["material"])

        # 사이즈
        await self.fill("input[name='size']", p["size"])

        # 컨디션
        condition_map = {"S": "미사용", "A": "거의새것", "B": "사용감있음", "C": "사용감많음"}
        await self.click(f"button:has-text('{condition_map[p['condition']]}')")

        # 가격
        await self.fill("input[name='price']", str(self.price))

        # 상세 설명 (에디터가 있으면 contenteditable 사용)
        editor = self.page.locator("[contenteditable='true']").first
        await editor.click()
        await editor.fill(p["description"])

        # 이미지 업로드
        await self.upload_images("input[type='file']")

    async def submit(self) -> None:
        await self.click("button:has-text('등록하기')")
        await self.page.wait_for_load_state("domcontentloaded")
