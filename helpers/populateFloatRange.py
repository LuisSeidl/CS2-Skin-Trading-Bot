from playwright.sync_api import sync_playwright, Playwright
import re
import enum
from typing import Optional
from entities import FloatRange, ExteriorType

FLOAT_CALC_URL = "https://stash.clash.gg/"
IGNORED_EXTERIORS = [ExteriorType.uncalculated, ExteriorType.not_painted, ExteriorType.unspecified]


class FloatRangePopulator():
    
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        
        self.page = self.browser.new_page()
        self.page.goto(FLOAT_CALC_URL)

        #banner = self.page.get_by_role("button", name="Maybe Later")
        #banner.wait_for(state="visible", timeout=5000)
        #if banner.is_visible():
        #    banner.click()

    def __shutdown__(self):
        self.browser.close()
        self.playwright.stop()

    def get_float_range(self, weapon_name: str) -> Optional[FloatRange]:
        """returns the float range for the skin, returns None if no float range is found"""

        #popup_close_button = self.page.locator(clash-popup)


        # Search for Item
        self.page.locator('.search-toggle').click()
        search_bar = self.page.locator(".search-bar")
        textbox = search_bar.get_by_placeholder("Search")
        textbox.fill(weapon_name)

        scroll_container = search_bar.locator(".scroll-container")
        scroll_container.wait_for()
        link = scroll_container.locator(".dropdown-item").nth(0)
        link.click()

        # Extract values
        extracted_data = {}

        wear_bar = self.page.locator(".wear-bar.text-center")

        for exterior in ExteriorType:
            if exterior in IGNORED_EXTERIORS:
                continue

            title_name = exterior.name.title()
            slug = title_name[0] + title_name.split("_")[-1][0]
            element = wear_bar.locator('div[data-container="body"]').get_by_text(f"{slug}", exact=False)

            if element.count() > 0:
                attribute = element.get_attribute("data-original-title")
                if attribute:
                    data = attribute.split(":")[1].strip().split("-")
                extracted_data[exterior.name] = {
                    "from": float(data[0]),
                    "to": float(data[1])
                }
            else:
                extracted_data[exterior.name] = {
                    "from": None,
                    "to": None
                }

        return FloatRange(
            name=weapon_name,
            factory_new_from=extracted_data["factory_new"]["from"],
            factory_new_to=extracted_data["factory_new"]["to"],
            minimal_wear_from=extracted_data["minimal_wear"]["from"],
            minimal_wear_to=extracted_data["minimal_wear"]["to"],
            field_tested_from=extracted_data["field_tested"]["from"],
            field_tested_to=extracted_data["field_tested"]["to"],
            well_worn_from=extracted_data["well_worn"]["from"],
            well_worn_to=extracted_data["well_worn"]["to"],
            battle_scarred_from=extracted_data["battle_scarred"]["from"],
            battle_scarred_to=extracted_data["battle_scarred"]["to"],
            not_painted=False
        )