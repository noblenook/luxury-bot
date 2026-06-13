from base_platform import BasePlatform


class Rebonz(BasePlatform):
    name = "리본즈"
    BASE = "https://www.rebonz.co.kr"

    async def login(self) -> None:
        await self.page.goto(f"{self.BASE}/login")
        await self.page.wait_for_load_state("domcontentloaded")
        await self.login_with_naver()

    async def navigate_to_register(self) -> None:
        await self.page.goto(f"{self.BASE}/mypage/product/write")
        await self.page.wait_for_load_state("domcontentloaded")

    async def fill_form(self) -> None:
        p = self.product

        # 이미지
        await self.upload_images("input[type='file']")

        # 카테고리 선택
        await self.click("select[name='cate1']")
        await self.select_option_by_text("select[name='cate1']", "가방")
        await self.page.wait_for_timeout(500)
        await self.select_option_by_text("select[name='cate2']", "숄더백")

        # 브랜드
        await self.fill("input[name='brand']", p["brand"])

        # 상품명
        await self.fill("input[name='goodsNm']", p["title_ko"])

        # 품번
        await self.fill("input[name='modelNo']", p["model_number"])

        # 색상
        await self.fill("input[name='color']", p["color"])

        # 소재
        await self.fill("input[name='material']", p["material"])

        # 사이즈
        await self.fill("input[name='size']", p["size"])

        # 컨디션
        condition_map = {"S": "S", "A": "A", "B": "B", "C": "C"}
        await self.click(f"input[value='{condition_map[p['condition']]}']")

        # 가격
        await self.fill("input[name='price']", str(self.price))

        # 구성품
        await self.fill("input[name='components']", self.accessories_text())

        # 상세 설명
        await self.fill("textarea[name='contents']", p["description"])

    async def submit(self) -> None:
        await self.click("button:has-text('등록')")
        await self.page.wait_for_load_state("domcontentloaded")
