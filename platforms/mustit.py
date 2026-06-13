from base_platform import BasePlatform


class Mustit(BasePlatform):
    name = "머스트잇"
    BASE = "https://www.mustit.co.kr"

    async def login(self) -> None:
        await self.page.goto(f"{self.BASE}/member/login")
        await self.page.wait_for_load_state("domcontentloaded")
        await self.login_with_naver()

    async def navigate_to_register(self) -> None:
        await self.page.goto(f"{self.BASE}/product/regist")
        await self.page.wait_for_load_state("domcontentloaded")

    async def fill_form(self) -> None:
        p = self.product

        # 카테고리
        await self.click("text=가방")
        await self.page.wait_for_timeout(300)
        await self.click("text=숄더백")

        # 브랜드
        await self.fill("input#brand_name", p["brand"])
        await self.page.wait_for_selector(".brand-list li", timeout=5000)
        await self.click(".brand-list li:first-child")

        # 상품명
        await self.fill("input#goods_name", p["title_ko"])

        # 모델넘버
        await self.fill("input#model_no", p["model_number"])

        # 색상
        await self.fill("input#color", p["color"])

        # 소재
        await self.fill("input#material", p["material"])

        # 사이즈
        await self.fill("input#size", p["size"])

        # 컨디션 (라디오)
        condition_map = {"S": "미사용", "A": "A급", "B": "B급", "C": "C급"}
        await self.click(f"label:has-text('{condition_map[p['condition']]}')")

        # 구성품 체크박스
        acc = p.get("accessories", {})
        checkboxes = {
            "guarantee_card": "보증서",
            "box": "박스",
            "dust_bag": "더스트백",
            "invoice": "인보이스",
            "receipt": "영수증",
            "booklet": "북렛",
            "tag": "택",
        }
        for key, label in checkboxes.items():
            if acc.get(key):
                try:
                    await self.click(f"label:has-text('{label}')")
                except Exception:
                    pass

        # 가격
        await self.fill("input#price", str(self.price))

        # 상세 설명
        await self.fill("textarea#detail_content", p["description"])

        # 이미지 업로드
        await self.upload_images("input[type='file']")

    async def submit(self) -> None:
        await self.click("button:has-text('상품 등록')")
        await self.page.wait_for_load_state("domcontentloaded")
