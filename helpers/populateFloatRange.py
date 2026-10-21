import requests
import re
import enum
from typing import Optional
from entities import FloatRange, ExteriorType

class FloatRangePopulator():
    _ROOT = "https://api.cs2.sh"
    _IGNORED_EXTERIORS = [ExteriorType.uncalculated, ExteriorType.not_painted, ExteriorType.unspecified]

    def __init__(self):
        pass


    def __shutdown__(self):
        pass

    def __call(self, )



    def get_float_range(self, weapon_name: str) -> Optional[FloatRange]:
        """returns the float range for the skin, returns None if no float range is found"""

        fr = FloatRange()

        # Search for Item
        self.page.locator('.search-toggle').click()
        search_bar = self.page.locator(".search-bar")
        textbox = search_bar.get_by_placeholder("Search")
        textbox.fill(weapon_name)

        try:
            scroll_container = search_bar.locator(".scroll-container")
            scroll_container.wait_for(timeout=1000)
            link = scroll_container.locator(".dropdown-item").nth(0)
            link.click()

            # Extract values
            extracted_data = {}
        except TimeoutError:
            return None
        
        try:
            wear_bar = self.page.locator(".wear-bar.text-center")
            wear_bar.wait_for(state="attached", timeout=3000)
        
            for exterior in ExteriorType:
                if exterior in IGNORED_EXTERIORS:
                    continue

                title_name = exterior.name.title()
                slug = title_name[0] + title_name.split("_")[-1][0]
                data_body = wear_bar.locator('div[data-container="body"]')
                data_body.wait_for(state="attached")
                element = data_body.get_by_text(f"{slug}", exact=False)
                if element.count() > 0:
                    data = None
                    attribute = element.get_attribute("data-original-title")
                    if attribute:
                        data = attribute.split(":")[1].strip().split("-")
                        if data and len(data) > 1:
                            extracted_data[exterior.name] = {
                                "from": float(data[0]),
                                "to": float(data[1])
                            }
                else:
                    extracted_data[exterior.name] = {
                        "from": None,
                        "to": None
                    }

            fr = FloatRange(
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

        except TimeoutError:

            fr = FloatRange(
                name="not_painted",
                factory_new_from=None,
                factory_new_to=None,
                minimal_wear_from=None,
                minimal_wear_to=None,
                field_tested_from=None,
                field_tested_to=None,
                well_worn_from=None,
                well_worn_to=None,
                battle_scarred_from=None,
                battle_scarred_to=None,
                not_painted=True
            )
        finally:
            if fr.isFalse():
                return None
            else:
                return fr