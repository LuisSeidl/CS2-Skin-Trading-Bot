from entities import ExteriorType

IGNORED_EXTERIORS = [ExteriorType.uncalculated, ExteriorType.not_painted, ExteriorType.unspecified]


for exterior in ExteriorType:
    if exterior in IGNORED_EXTERIORS:
        continue

    title_name = exterior.name.title()
    slug = title_name[0] + title_name.split("_")[-1][0]
    print(slug)