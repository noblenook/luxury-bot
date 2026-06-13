from base_platform import BasePlatform


class Feelway(BasePlatform):
    name = "필웨이"
    BASE = "https://www.feelway.com"

    async def login(self) -> None:
        await self.page.goto(f"{self.BASE}/member/login.gd")
        await self.fill("input[name='m_id']", self.cred["id"])
        await self.fill("input[name='m_pw']", self.cred["password"])
        await self.click("input[type='submit']")
        await self.page.wait_for_load_state("domcontentloaded")

    async def navigate_to_register(self) -> None:
        await self.page.goto(f"{self.BASE}/goods/goods_write.gd")
        await self.page.wait_for_load_state("domcontentloaded")

    async def fill_form(self) -> None:
        p = self.product

        # 이미지 업로드
        await self.upload_images("input[type='file']")

        # 상품명
        await self.fill("input[name='g_name']", p["title_ko"])

        # 브랜드
        await self.fill("input[name='g_brand']", p["brand"])

        # 품번
        await self.fill("input[name='g_model']", p["model_number"])

        # 컬러
        await self.fill("input[name='g_color']", p["color"])

        # 사이즈/소재
        await self.fill("input[name='g_size']", p["size"])

        # 가격
        await self.fill("input[name='g_price']", str(self.price))

        # 컨디션 등급 (라디오 또는 select)
        condition_map = {"S": "S급", "A": "A급", "B": "B급", "C": "C급"}
        await self.click(f"label:has-text('{condition_map[p['condition']]}')")

        # 구성품 체크박스
        acc = p.get("accessories", {})
        if acc.get("guarantee_card"):
            await self.click("label:has-text('보증서')")
        if acc.get("box"):
            await self.click("label:has-text('박스')")
        if acc.get("dust_bag"):
            await self.click("label:has-text('더스트백')")

        # 상세 설명
        await self.fill("textarea[name='g_memo']", p["description"])

    async def submit(self) -> None:
        await self.click("input[value='상품등록']")
        await self.page.wait_for_load_state("domcontentloaded")
