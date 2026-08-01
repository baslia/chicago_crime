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
# Goal: every crime type is *easily* distinguishable from its neighbors, while
# the palette still reads as serious (deep Material-Design 700-level tones, all
# legible on the light map — no pastels, no neon).
#
# The legend is rendered in alphabetical order, so the trick is to assign colors
# in alphabetical order too, cycling a palette whose *consecutive* entries are
# maximally far apart on the color wheel. That guarantees neighbouring legend
# rows never look alike. Categories are intentionally NOT grouped by hue —
# grouping (all "violent" = reds) is precisely what made colors blur together.
DISTINCT_PALETTE: list[str] = [
    "#d32f2f",  # red
    "#1976d2",  # blue
    "#388e3c",  # green
    "#f57c00",  # orange
    "#7b1fa2",  # purple
    "#0097a7",  # cyan
    "#5d4037",  # brown
    "#c2185b",  # pink
    "#9e9d24",  # olive
    "#303f9f",  # indigo
    "#00796b",  # teal
    "#f9a825",  # amber
    "#512da8",  # deep purple
    "#689f38",  # light green
    "#0288d1",  # light blue
    "#e64a19",  # deep orange
    "#455a64",  # blue-grey
    "#ad1457",  # dark pink
    "#b71c1c",  # dark red
    "#004d40",  # dark teal
    "#4a148c",  # dark purple
    "#33691e",  # dark green
    "#bf360c",  # rust
    "#01579b",  # dark blue (kept last: far from the red at index 0 on wrap)
]

# Canonical set of Chicago `primary_type` values (both historical and current
# spellings). Sorted, then zipped with the cycled palette for stable colors.
_KNOWN_TYPES: list[str] = sorted({
    "ARSON", "ASSAULT", "BATTERY", "BURGLARY",
    "CONCEALED CARRY LICENSE VIOLATION", "CRIM SEXUAL ASSAULT",
    "CRIMINAL DAMAGE", "CRIMINAL SEXUAL ASSAULT", "CRIMINAL TRESPASS",
    "DECEPTIVE PRACTICE", "DOMESTIC VIOLENCE", "GAMBLING", "HOMICIDE",
    "HUMAN TRAFFICKING", "INTERFERENCE WITH PUBLIC OFFICER", "INTIMIDATION",
    "KIDNAPPING", "LIQUOR LAW VIOLATION", "MOTOR VEHICLE THEFT", "NARCOTICS",
    "NON-CRIMINAL", "OBSCENITY", "OFFENSE INVOLVING CHILDREN",
    "OTHER NARCOTIC VIOLATION", "OTHER OFFENSE", "PROSTITUTION",
    "PUBLIC INDECENCY", "PUBLIC PEACE VIOLATION", "RITUALISM", "ROBBERY",
    "SEX OFFENSE", "STALKING", "THEFT", "WEAPONS VIOLATION",
})

CRIME_TYPE_COLORS: dict[str, str] = {
    t: DISTINCT_PALETTE[i % len(DISTINCT_PALETTE)]
    for i, t in enumerate(_KNOWN_TYPES)
}

# Neutral blue-grey for any truly unknown type (rare).
OTHER_COLOR = "#78909c"


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
