"""Static configuration for the Chicago Crime dashboard.

The data comes from the City of Chicago "Crimes - 2001 to Present" dataset,
served through the Socrata Open Data API (SODA).

Dataset landing page:
    https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2
"""

from __future__ import annotations

# --- Socrata / SODA -----------------------------------------------------------
SOCRATA_DOMAIN = "data.cityofchicago.org"
DATASET_ID = "ijzp-q8t2"

# Columns we actually use, keeps the payload small.
INCIDENT_COLUMNS = [
    "id",
    "date",
    "primary_type",
    "description",
    "location_description",
    "arrest",
    "domestic",
    "district",
    "ward",
    "community_area",
    "block",
    "latitude",
    "longitude",
    "year",
]

# Hard cap on markers pulled for the map. Plotting more than this in a browser
# via Leaflet becomes painful even with clustering.
MAX_MAP_POINTS = 5000

# Chicago city center, for the default map view.
CHICAGO_CENTER = (41.8781, -87.6298)
DEFAULT_ZOOM = 11

# Earliest year present in the dataset.
MIN_YEAR = 2001

# --- Crime-type colors --------------------------------------------------------
# A stable, readable palette for the most common primary types. Anything not
# listed falls back to OTHER_COLOR. Colors are chosen to be distinguishable and
# color-blind friendly-ish; tweak freely.
CRIME_TYPE_COLORS: dict[str, str] = {
    "THEFT": "#4e79a7",
    "BATTERY": "#e15759",
    "CRIMINAL DAMAGE": "#f28e2b",
    "NARCOTICS": "#76b7b2",
    "ASSAULT": "#b07aa1",
    "OTHER OFFENSE": "#9c755f",
    "BURGLARY": "#edc948",
    "MOTOR VEHICLE THEFT": "#59a14f",
    "DECEPTIVE PRACTICE": "#ff9da7",
    "ROBBERY": "#bab0ac",
    "CRIMINAL TRESPASS": "#86bcb6",
    "WEAPONS VIOLATION": "#d37295",
    "OFFENSE INVOLVING CHILDREN": "#a0cbe8",
    "PUBLIC PEACE VIOLATION": "#8cd17d",
    "CRIM SEXUAL ASSAULT": "#b6992d",
    "SEX OFFENSE": "#499894",
    "HOMICIDE": "#000000",
}
OTHER_COLOR = "#7f7f7f"


def color_for(primary_type: str) -> str:
    """Return the marker color for a given primary crime type."""
    return CRIME_TYPE_COLORS.get((primary_type or "").upper(), OTHER_COLOR)


# --- Crime groups (clusters) --------------------------------------------------
# High-level shortcuts that expand into the dataset's fine-grained `primary_type`
# values. Selecting a group filters to all of its types; the individual-type
# drilldown still works alongside these. A group may hold one type or many.
# Both historical and current spellings are included (e.g. sexual assault) so the
# filter matches regardless of when the incident was recorded; unmatched spellings
# simply return nothing and are harmless.
CRIME_GROUPS: dict[str, list[str]] = {
    "Violent": [
        "HOMICIDE", "CRIMINAL SEXUAL ASSAULT", "CRIM SEXUAL ASSAULT", "ASSAULT",
        "BATTERY", "ROBBERY", "KIDNAPPING", "INTIMIDATION", "HUMAN TRAFFICKING",
    ],
    "Property": [
        "THEFT", "BURGLARY", "MOTOR VEHICLE THEFT", "CRIMINAL DAMAGE",
        "CRIMINAL TRESPASS", "ARSON", "DECEPTIVE PRACTICE",
    ],
    "Drugs & Vice": [
        "NARCOTICS", "OTHER NARCOTIC VIOLATION", "PROSTITUTION", "GAMBLING",
        "LIQUOR LAW VIOLATION", "OBSCENITY", "PUBLIC INDECENCY",
    ],
    "Weapons": ["WEAPONS VIOLATION", "CONCEALED CARRY LICENSE VIOLATION"],
    "Sexual": [
        "CRIMINAL SEXUAL ASSAULT", "CRIM SEXUAL ASSAULT", "SEX OFFENSE", "STALKING",
    ],
    "Public order": [
        "PUBLIC PEACE VIOLATION", "INTERFERENCE WITH PUBLIC OFFICER",
        "OTHER OFFENSE", "NON-CRIMINAL", "NON - CRIMINAL",
    ],
    "Domestic-related": ["OFFENSE INVOLVING CHILDREN"],
}


def expand_groups(group_names) -> tuple[str, ...]:
    """Union the primary types covered by the named groups (order-stable, deduped)."""
    seen: dict[str, None] = {}
    for name in group_names:
        for t in CRIME_GROUPS.get(name, []):
            seen.setdefault(t, None)
    return tuple(seen)


# --- Community areas ----------------------------------------------------------
# Chicago's 77 official community areas. The dataset stores `community_area` as
# the numeric code; this maps it to a human-readable name for the geo view.
COMMUNITY_AREAS: dict[int, str] = {
    1: "Rogers Park", 2: "West Ridge", 3: "Uptown", 4: "Lincoln Square",
    5: "North Center", 6: "Lake View", 7: "Lincoln Park", 8: "Near North Side",
    9: "Edison Park", 10: "Norwood Park", 11: "Jefferson Park", 12: "Forest Glen",
    13: "North Park", 14: "Albany Park", 15: "Portage Park", 16: "Irving Park",
    17: "Dunning", 18: "Montclare", 19: "Belmont Cragin", 20: "Hermosa",
    21: "Avondale", 22: "Logan Square", 23: "Humboldt Park", 24: "West Town",
    25: "Austin", 26: "West Garfield Park", 27: "East Garfield Park",
    28: "Near West Side", 29: "North Lawndale", 30: "South Lawndale",
    31: "Lower West Side", 32: "Loop", 33: "Near South Side", 34: "Armour Square",
    35: "Douglas", 36: "Oakland", 37: "Fuller Park", 38: "Grand Boulevard",
    39: "Kenwood", 40: "Washington Park", 41: "Hyde Park", 42: "Woodlawn",
    43: "South Shore", 44: "Chatham", 45: "Avalon Park", 46: "South Chicago",
    47: "Burnside", 48: "Calumet Heights", 49: "Roseland", 50: "Pullman",
    51: "South Deering", 52: "East Side", 53: "West Pullman", 54: "Riverdale",
    55: "Hegewisch", 56: "Garfield Ridge", 57: "Archer Heights", 58: "Brighton Park",
    59: "McKinley Park", 60: "Bridgeport", 61: "New City", 62: "West Elsdon",
    63: "Gage Park", 64: "Clearing", 65: "West Lawn", 66: "Chicago Lawn",
    67: "West Englewood", 68: "Englewood", 69: "Greater Grand Crossing",
    70: "Ashburn", 71: "Auburn Gresham", 72: "Beverly", 73: "Washington Heights",
    74: "Mount Greenwood", 75: "Morgan Park", 76: "O'Hare", 77: "Edgewater",
}


def community_area_name(code) -> str:
    """Map a community-area code to its name, tolerating strings/None."""
    try:
        return COMMUNITY_AREAS.get(int(float(code)), f"Area {code}")
    except (TypeError, ValueError):
        return "Unknown"
