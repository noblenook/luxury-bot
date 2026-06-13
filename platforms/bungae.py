from base_platform import BasePlatform


class Bungae(BasePlatform):
    name = "번개장터"
    BASE = "https://www.bunjang.co.kr"

    async def login(self) -> None:
        pass  # navigate_to_register에서 통합 처리

    async def navigate_to_register(self) -> None:
        await self.page.goto(f"{self.BASE}/products/new", wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1500)

        # 등록 페이지로 이동했는지 확인 — 리다이렉트됐으면 로그인 필요
        if "/products/new" not in self.page.url:
            print(f"  [{self.name}] 세션 없음 → 네이버 로그인 후 재이동")
            await self.page.goto(f"{self.BASE}/login", wait_until="domcontentloaded")
            await self.page.wait_for_timeout(1000)
            await self.login_with_naver("button:has-text('네이버로 로그인')")
            await self.page.goto(f"{self.BASE}/products/new", wait_until="domcontentloaded")
            await self.page.wait_for_timeout(1500)

        print(f"  [{self.name}] 등록 페이지 도달 — URL: {self.page.url}")
        await self.screenshot("bungae_02_register.png")

    async def fill_form(self) -> None:
        p = self.product
        print(f"  [{self.name}] 폼 입력 시작 — URL: {self.page.url}")
        print(f"  [{self.name}] 이미지 수: {len(self.images)}")
        await self.screenshot("bungae_03_form_start.png")

        # ── 1. 이미지 ──────────────────────────────────────────
        print(f"  [{self.name}] 이미지 업로드 중...")
        await self.page.wait_for_timeout(1500)
        if self.images:
            await self.page.locator("#media-input").set_input_files(self.images)
            await self.page.wait_for_timeout(2500)
        await self.screenshot("bungae_04_image.png")
        print(f"  [{self.name}] 이미지 완료")

        # ── 2. 상품명 ───────────────────────────────────────────
        print(f"  [{self.name}] 상품명 입력 중...")
        title = self.page.locator("input[placeholder='상품명을 입력해 주세요.']")
        await title.wait_for(timeout=10000)
        await title.fill(p["title_ko"])
        await self.screenshot("bungae_04_title.png")
        print(f"  [{self.name}] 상품명 완료")

        # ── 3. 카테고리 ─────────────────────────────────────────
        print(f"  [{self.name}] 카테고리 선택 중...")
        for label in ["패션잡화", "가방", "숄더"]:
            try:
                item = self.page.locator(f"li:has-text('{label}')").first
                await item.wait_for(timeout=5000)
                await item.click()
                await self.page.wait_for_timeout(600)
            except Exception:
                pass
        await self.screenshot("bungae_05_category.png")
        print(f"  [{self.name}] 카테고리 완료")

        # ── 4. 가격 ─────────────────────────────────────────────
        print(f"  [{self.name}] 가격 입력 중...")
        price_input = self.page.locator("input[placeholder*='가격']").first
        await price_input.wait_for(timeout=10000)
        await price_input.fill(str(self.price))
        await self.screenshot("bungae_06_price.png")
        print(f"  [{self.name}] 가격 완료")

        # ── 5. 상품 상태 드롭다운 ────────────────────────────────
        condition_map = {
            "N":  "새 상품 (미사용)",
            "S":  "사용감 없음",
            "A+": "사용감 없음",
            "A":  "사용감 적음",
            "B":  "사용감 많음",
            "C":  "고장/파손 상품",
        }
        cond_label = condition_map.get(p["condition"], "사용감 없음")

        cond_trigger = self.page.locator("text=상품 상태를 선택해 주세요").first
        await cond_trigger.wait_for(timeout=10000)
        await cond_trigger.click()
        await self.page.wait_for_timeout(600)

        # 옵션 텍스트 앞부분으로 매칭 (괄호 포함 전체 or 첫 단어)
        opt = self.page.locator(f"text={cond_label}").first
        await opt.wait_for(timeout=5000)
        await opt.click()
        await self.page.wait_for_timeout(400)
        await self.screenshot("bungae_07_condition_done.png")

        # ── 6. 설명 ─────────────────────────────────────────────
        # product.txt가 있으면 그 내용을, 없으면 자동 생성 텍스트 사용
        desc_text = self.description if self.description else self._build_description(p)
        desc = self.page.locator("textarea").first
        await desc.wait_for(timeout=10000)
        await desc.fill(desc_text)
        await self.screenshot("bungae_08_desc.png")

        # ── 7. 태그 (선택) ───────────────────────────────────────
        tags = ["샤넬", "클래식플랩", "명품가방", "캐비어", "금장"]
        try:
            tag_input = self.page.locator("input[placeholder*='태그']").first
            await tag_input.wait_for(timeout=5000)
            for tag in tags:
                await tag_input.click()
                await tag_input.fill(tag)
                await self.page.wait_for_timeout(200)
                await self.page.keyboard.press("Space")  # 번개장터 태그는 스페이스로 구분
                await self.page.wait_for_timeout(300)
        except Exception as e:
            print(f"  [{self.name}] 태그 입력 건너뜀: {e}")
        await self.screenshot("bungae_09_tags.png")

    async def submit(self) -> None:
        await self.screenshot("bungae_10_before_submit.png")
        submit_btn = self.page.locator("button:has-text('등록하기')").first
        await submit_btn.wait_for(timeout=10000)
        await submit_btn.click()
        await self.page.wait_for_load_state("domcontentloaded")
        await self.screenshot("bungae_11_done.png")

    def _build_description(self, p: dict) -> str:
        return (
            f"[상품정보]\n"
            f"브랜드: {p['brand']}\n"
            f"상품명: {p['title_ko']}\n"
            f"품번: {p['model_number']} ({p['serial_number']})\n"
            f"사이즈: {p['size']}\n"
            f"소재: {p['material']}\n"
            f"색상: {p['color']}\n"
            f"하드웨어: {p['hardware']}\n"
            f"컨디션: {p['condition']}등급\n"
            f"구성품: {self.accessories_text()}\n\n"
            f"[상품설명]\n{p['description']}\n\n"
            f"[상태상세]\n{p['condition_detail']}\n\n"
            f"[안내사항]\n"
            f"· 명품 전문 감정사의 감정을 거쳐 정품 인증을 완료한 상품입니다.\n"
            f"· 보안 태그 훼손/제거 시 교환·반품 불가합니다."
        )
