from playwright.sync_api import sync_playwright, Playwright
import re
import enum
from typing import Optional
from entities import FloatRange, ExteriorType

FLOAT_CALC_URL = "https://cs2floatchecker.com/tools/float-database"
PLACEHOLDER = "Search for a skin (e.g., AK-47 Redline, AWP Dragon Lore)..."

class FloatRangePopulator():
    
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        
        self.page = self.browser.new_page()
        self.page.goto(FLOAT_CALC_URL)

        banner = self.page.get_by_role("button", name="Maybe Later")
        banner.wait_for(state="visible", timeout=5000)
        if banner.is_visible():
            banner.click()

    def __shutdown__(self):
        self.browser.close()
        self.playwright.stop()

    def get_float_range(self, full_name: str) -> Optional[FloatRange]:
        """returns the float range for the skin, returns None if no float range is found"""
        textbox = self.page.get_by_placeholder(PLACEHOLDER)
        textbox.fill(full_name)

        # Get card containing the Item
        card = self.page.locator('div[data-slot="card"]').filter(has_text=full_name).nth(0)
        card.locator('.cursor-pointer').first.click()
        
        # Get min and max float values 
        min_max_span = card.get_by_text("Float:")
        min_float = min_max_span.locator("span.font-mono").nth(0).text_content()
        max_float = min_max_span.locator("span.font-mono").nth(1).text_content()
        min_val = float(min_float) if min_float else None
        max_val = float(max_float) if max_float else None

        if min_val is None or max_val is None:
            return FloatRange(
                name= "not_painted",
                not_painted = True
            )
        extracted_data = {}

        # Get all available Wear conditions
        conditions_list_elem = self.page.locator('div[data-slot="card"]').filter(has_text=full_name)
        conditions_list_elem.wait_for(state="visible", timeout=5000)

        for exterior in ExteriorType:
            if exterior == ExteriorType.not_painted:
                continue
            
            title_name = exterior.value.title()
            element = conditions_list_elem.locator('span[data-slot="badge"]').get_by_text(title_name, exact=True)
        
            if not element.is_visible(timeout=0):
                extracted_data[exterior.name] = {
                    "from": None,
                    "to": None
                }
                continue

        # Get min and max for all exterior types which exist for this skin
        float_val_div = card.locator('div[class="bg-secondary relative mb-4 h-8 overflow-hidden rounded-lg"]')

        for exterior in ExteriorType:
            if exterior == ExteriorType.not_painted:
                continue

            if extracted_data.get(exterior.name) is not None:
                continue

            title_name = exterior.value.title()

            element = float_val_div.get_by_title(title_name)

            if element.count() == 0:
                continue

            style_text = element.get_attribute("style")
            
            left_match = re.search(r"left:\s*(\d+.?\d*)%", style_text)
            width_match = re.search(r"width:\s*(\d+.?\d*)%", style_text)

            left_val = float(left_match.group(1)) if left_match else None
            width_val = float(width_match.group(1)) if width_match else None

            extracted_data[exterior.name] = {
                "from": left_val / 100,
                "to": (left_val+width_val) / 100
            }


        for item in extracted_data.items():
            if item[1]["from"] is None:
                continue

            if item[1]["from"] < min_val:
                item[1]["from"] = min_val

            if item[1]["to"] > max_val:
                item[1]["to"] = max_val


        return FloatRange(
            name=full_name,
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