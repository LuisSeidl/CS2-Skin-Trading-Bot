import enum
from typing import Optional

_DMARKET_QUALITY_MAP: dict[str, str] = {
    # Standard grades
    "QUALITY_UNSPECIFIED":      "unspecified",
    "QUALITY_CONSUMER_GRADE":   "consumer",
    "QUALITY_INDUSTRIAL_GRADE": "industrial",
    "QUALITY_MIL_SPEC":         "mil_spec",
    "QUALITY_RESTRICTED":       "restricted",
    "QUALITY_CLASSIFIED":       "classified",
    "QUALITY_COVERT":           "covert",
    "QUALITY_DISTINGUISHED":    "distinguished",
    "QUALITY_EXCEPTIONAL":      "exceptional",
    "QUALITY_SUPERIOR":         "superior",
    "QUALITY_MASTER":           "master",
    "QUALITY_BASE_GRADE":       "base_grade",
    "QUALITY_EXTRAORDINARY":    "extraordinary",
    "QUALITY_HIGH_GRADE":       "high_grade",
    "QUALITY_REMARKABLE":       "remarkable",
    "QUALITY_EXOTIC":           "exotic",
    "QUALITY_CONTRABAND":       "contraband",
    "QUALITY_STOCK":            "stock",
}

_DMARKET_EXTERIOR_MAP: dict[str, str] = {
    "EXTERIOR_UNSPECIFIED":     "unspecified",
    "EXTERIOR_FACTORY_NEW":     "factory_new",
    "EXTERIOR_MINIMAL_WEAR":    "minimal_wear",
    "EXTERIOR_FIELD_TESTED":    "field_tested",
    "EXTERIOR_WELL_WORN":       "well_worn",
    "EXTERIOR_BATTLE_SCARRED":  "battle_scarred",
    "EXTERIOR_NOT_PAINTED":     "not_painted",

}