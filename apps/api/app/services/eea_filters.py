"""EEA geography, seniority, visa, and English validation helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

# ISO-ish country names/codes commonly seen in job posts (EEA + Norway/Iceland/Liechtenstein)
EEA_COUNTRIES: dict[str, str] = {
    "at": "Austria",
    "be": "Belgium",
    "bg": "Bulgaria",
    "hr": "Croatia",
    "cy": "Cyprus",
    "cz": "Czechia",
    "dk": "Denmark",
    "ee": "Estonia",
    "fi": "Finland",
    "fr": "France",
    "de": "Germany",
    "gr": "Greece",
    "hu": "Hungary",
    "is": "Iceland",
    "ie": "Ireland",
    "it": "Italy",
    "lv": "Latvia",
    "li": "Liechtenstein",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "mt": "Malta",
    "nl": "Netherlands",
    "no": "Norway",
    "pl": "Poland",
    "pt": "Portugal",
    "ro": "Romania",
    "sk": "Slovakia",
    "si": "Slovenia",
    "es": "Spain",
    "se": "Sweden",
}

EEA_NAME_TO_CODE = {name.lower(): code for code, name in EEA_COUNTRIES.items()}
# Aliases
EEA_NAME_TO_CODE.update(
    {
        "netherlands": "nl",
        "holland": "nl",
        "czech republic": "cz",
        "czechia": "cz",
        "united kingdom": "xx",  # not EEA — used to reject
        "uk": "xx",
        "great britain": "xx",
        "switzerland": "xx",
        "usa": "xx",
        "united states": "xx",
    }
)

SENIOR_TITLE_PATTERNS = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\blead\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bhead of\b",
    r"\bvp\b",
    r"\bvice president\b",
    r"\barchitect\b",
    r"\bchief\b",
]

PREFERRED_TITLE_PATTERNS = [
    r"software engineer",
    r"software developer",
    r"full[\s-]?stack",
    r"backend",
    r"front[\s-]?end",
    r"web developer",
    r"application developer",
    r"software development engineer",
    r"\bjunior\b",
    r"\bmid[\s-]?level\b",
    r"\bassociate\b",
]

VISA_BLOCK_PATTERNS = [
    r"must (already )?have (unrestricted )?(work )?authorization",
    r"must be (an? )?(eu|eea|local) citizen",
    r"no(\s+visa)?\s+sponsorship",
    r"cannot sponsor",
    r"unable to sponsor",
    r"unable to provide (a )?(work permit|visa|sponsorship)",
    r"cannot provide (a )?(work permit|visa|sponsorship)",
    r"not able to (sponsor|provide (a )?(work permit|visa))",
    r"will not sponsor",
    r"does not (provide|offer|support) (visa|work permit|sponsorship)",
    r"no work (permit|visa) (support|sponsorship)",
    r"sponsorship is not available",
    r"only candidates (who are )?authorized to work",
    r"must have (the )?right to work",
]

# Languages other than English. A required second language fails the "English only" rule.
_OTHER_LANGS = (
    "dutch|german|french|spanish|italian|swedish|norwegian|danish|finnish|"
    "polish|portuguese|czech|hungarian|romanian|greek|mandarin|chinese|"
    "japanese|korean|arabic|turkish|ukrainian|russian"
)
ADDITIONAL_LANGUAGE_PATTERNS = [
    rf"\b(fluent|native|proficient|advanced)\s+(in\s+)?({_OTHER_LANGS})\b",
    rf"\b({_OTHER_LANGS})\b\s+(language\s+)?(required|mandatory|is required|is a must|essential)\b",
    rf"\bmust\s+(also\s+)?(speak|write|be fluent in)\s+({_OTHER_LANGS})\b",
    rf"\bworking language[:\s]+({_OTHER_LANGS})\b",
]

EUROPE_EXTRA: dict[str, str] = {
    "united kingdom": "gb",
    "great britain": "gb",
    "england": "gb",
    "scotland": "gb",
    "wales": "gb",
    "london": "gb",
    "switzerland": "ch",
    "zurich": "ch",
    "geneva": "ch",
    "europe": "eu",
    "european union": "eu",
}

JOB_REGIONS: tuple[str, ...] = (
    "Europe",
    "North America",
    "South America",
    "Asia",
    "Africa",
)

_REGION_MARKERS: dict[str, tuple[str, ...]] = {
    "North America": (
        "north america",
        "united states",
        "usa",
        "u.s.a",
        "u.s.",
        "canada",
        "mexico",
        "toronto",
        "montreal",
        "vancouver",
        "ottawa",
        "mexico city",
        "san francisco",
        "new york",
        "seattle",
        "austin",
        "boston",
        "chicago",
        "los angeles",
        "denver",
        "atlanta",
        "miami",
        "dallas",
        "houston",
        "washington, dc",
        "washington dc",
    ),
    "South America": (
        "south america",
        "brazil",
        "brasil",
        "argentina",
        "chile",
        "colombia",
        "peru",
        "uruguay",
        "ecuador",
        "bolivia",
        "paraguay",
        "venezuela",
        "sao paulo",
        "são paulo",
        "buenos aires",
        "santiago",
        "lima",
        "bogota",
        "bogotá",
    ),
    "Asia": (
        "asia",
        "india",
        "singapore",
        "japan",
        "china",
        "south korea",
        "korea",
        "hong kong",
        "taiwan",
        "vietnam",
        "indonesia",
        "thailand",
        "malaysia",
        "philippines",
        "pakistan",
        "bangladesh",
        "sri lanka",
        "israel",
        "united arab emirates",
        "uae",
        "dubai",
        "qatar",
        "saudi arabia",
        "tokyo",
        "seoul",
        "bangalore",
        "bengaluru",
        "mumbai",
        "hyderabad",
        "delhi",
        "pune",
        "jakarta",
        "bangkok",
        "kuala lumpur",
        "manila",
        "tel aviv",
        "beijing",
        "shanghai",
        "shenzhen",
        "osaka",
    ),
    "Africa": (
        "africa",
        "south africa",
        "nigeria",
        "kenya",
        "egypt",
        "ghana",
        "morocco",
        "tunisia",
        "rwanda",
        "ethiopia",
        "uganda",
        "tanzania",
        "cape town",
        "johannesburg",
        "lagos",
        "nairobi",
        "cairo",
        "accra",
    ),
}

# Central country-to-continent mapping. Transcontinental countries use one
# canonical region (Russia -> Europe; Turkey/Kazakhstan -> Asia) for filtering.
_CONTINENT_COUNTRY_CODES: dict[str, set[str]] = {
    "Europe": {
        "AL", "AD", "AT", "BY", "BE", "BA", "BG", "HR", "CY", "CZ", "DK", "EE", "FI",
        "FR", "DE", "GR", "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU", "MT", "MD",
        "MC", "ME", "NL", "MK", "NO", "PL", "PT", "RO", "RU", "SM", "RS", "SK", "SI",
        "ES", "SE", "CH", "UA", "GB", "VA", "XK", "GG", "IM", "JE", "FO", "GI",
    },
    "North America": {
        "US", "CA", "MX", "GL", "BM", "PM", "BZ", "CR", "SV", "GT", "HN", "NI", "PA",
        "CU", "JM", "HT", "DO", "PR", "BS", "BB", "TT", "GD", "LC", "VC", "AG", "DM",
        "KN", "AI", "AW", "CW", "SX", "BQ", "KY", "TC", "VG", "VI", "GP", "MQ", "BL", "MF",
    },
    "South America": {
        "AR", "BO", "BR", "CL", "CO", "EC", "FK", "GF", "GY", "PE", "PY", "SR", "UY", "VE",
    },
    "Asia": {
        "AF", "AM", "AZ", "BH", "BD", "BT", "BN", "KH", "CN", "CX", "CC", "GE", "HK", "IN",
        "ID", "IR", "IQ", "IL", "JP", "JO", "KZ", "KP", "KR", "KW", "KG", "LA", "LB", "MO",
        "MY", "MV", "MN", "MM", "NP", "OM", "PK", "PS", "PH", "QA", "SA", "SG", "LK", "SY",
        "TW", "TJ", "TH", "TL", "TR", "TM", "AE", "UZ", "VN", "YE",
    },
    "Africa": {
        "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CG", "CD", "CI",
        "DJ", "EG", "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR",
        "LY", "MG", "MW", "ML", "MR", "MU", "YT", "MA", "MZ", "NA", "NE", "NG", "RE", "RW",
        "SH", "ST", "SN", "SC", "SL", "SO", "ZA", "SS", "SD", "TZ", "TG", "TN", "UG", "EH",
        "ZM", "ZW",
    },
}

_CONTINENT_COUNTRY_NAMES: dict[str, tuple[str, ...]] = {
    "Europe": (
        "albania", "andorra", "austria", "belarus", "belgium", "bosnia and herzegovina",
        "bulgaria", "croatia", "cyprus", "czechia", "czech republic", "denmark", "estonia",
        "finland", "france", "germany", "greece", "hungary", "iceland", "ireland", "italy",
        "kosovo", "latvia", "liechtenstein", "lithuania", "luxembourg", "malta", "moldova",
        "monaco", "montenegro", "netherlands", "north macedonia", "norway", "poland",
        "portugal", "romania", "san marino", "serbia", "slovakia", "slovenia", "spain",
        "sweden", "switzerland", "ukraine", "united kingdom", "great britain", "england",
        "scotland", "wales", "vatican city", "russia",
    ),
    "North America": (
        "united states", "united states of america", "usa", "canada", "mexico", "greenland",
        "belize", "costa rica", "el salvador", "guatemala", "honduras", "nicaragua", "panama",
        "antigua and barbuda", "bahamas", "barbados", "cuba", "dominica", "dominican republic",
        "grenada", "haiti", "jamaica", "saint kitts and nevis", "saint lucia",
        "saint vincent and the grenadines", "trinidad and tobago", "puerto rico", "bermuda",
    ),
    "South America": (
        "argentina", "bolivia", "brazil", "brasil", "chile", "colombia", "ecuador", "guyana",
        "paraguay", "peru", "suriname", "uruguay", "venezuela", "french guiana",
    ),
    "Asia": (
        "afghanistan", "armenia", "azerbaijan", "bahrain", "bangladesh", "bhutan", "brunei",
        "cambodia", "china", "hong kong", "india", "indonesia", "iran", "iraq",
        "israel", "japan", "jordan", "kazakhstan", "kuwait", "kyrgyzstan", "laos", "lebanon",
        "malaysia", "maldives", "mongolia", "myanmar", "nepal", "north korea", "oman",
        "pakistan", "palestine", "philippines", "qatar", "saudi arabia", "singapore", "south korea",
        "sri lanka", "syria", "taiwan", "tajikistan", "thailand", "timor-leste", "turkey",
        "turkmenistan", "united arab emirates", "uzbekistan", "vietnam", "yemen", "macau",
    ),
    "Africa": (
        "algeria", "angola", "benin", "botswana", "burkina faso", "burundi", "cape verde",
        "cameroon", "central african republic", "chad", "comoros", "republic of the congo",
        "democratic republic of the congo", "ivory coast", "cote d'ivoire", "djibouti", "egypt",
        "equatorial guinea", "eritrea", "eswatini", "ethiopia", "gabon", "gambia", "ghana",
        "guinea", "guinea-bissau", "kenya", "lesotho", "liberia", "libya", "madagascar",
        "malawi", "mali", "mauritania", "mauritius", "morocco", "mozambique", "namibia",
        "niger", "nigeria", "rwanda", "senegal", "seychelles", "sierra leone", "somalia",
        "south africa", "south sudan", "sudan", "tanzania", "togo", "tunisia", "uganda",
        "western sahara", "zambia", "zimbabwe",
    ),
}

_CITY_REGION_MARKERS: dict[str, tuple[str, ...]] = {
    "Europe": tuple(EUROPE_EXTRA) + (
        "amsterdam", "berlin", "paris", "madrid", "rome", "dublin", "zurich", "stockholm",
        "warsaw", "lisbon",
    ),
    "North America": _REGION_MARKERS["North America"],
    "South America": _REGION_MARKERS["South America"],
    "Asia": _REGION_MARKERS["Asia"],
    "Africa": _REGION_MARKERS["Africa"],
}

_SENIORITY_CUES = (
    r"\bsenior(?:-level)?\b", r"\bsr\.?\b", r"\bstaff(?:-level)?\b",
    r"\bprincipal\b", r"\bdistinguished\b", r"\bdirector\b", r"\bhead of\b",
    r"\bvice president\b", r"\bvp\b", r"\bchief\b", r"\bmanager\b",
)
_NON_SENIORITY_CUES = (
    r"\bjunior(?:-level)?\b", r"\bentry[ -]level\b", r"\bgraduate\b",
    r"\bassociate\b", r"\bmid[ -]level\b", r"\bearly[ -]career\b", r"\bintern\b",
)


def classify_job_seniority(item: Any) -> str:
    """Classify as senior/non_senior; ambiguous or conflicting evidence is unknown."""
    title = str(item.title or "")
    description = " ".join(
        [str(item.description or ""), *(str(value) for value in (item.requirements or [])),
         *(str(value) for value in (item.responsibilities or []))]
    )
    raw = item.raw_payload or {}
    label = str(
        item.seniority_label
        or raw.get("seniorityLevel")
        or raw.get("seniority_label")
        or raw.get("experienceLevel")
        or raw.get("seniority")
        or ""
    )
    title_lower = title.lower()
    text = f"{title} {description}".lower()
    label_lower = label.lower()
    senior = any(re.search(pattern, label_lower) for pattern in _SENIORITY_CUES)
    non_senior = any(re.search(pattern, label_lower) for pattern in _NON_SENIORITY_CUES)
    senior = senior or any(re.search(pattern, title_lower) for pattern in _SENIORITY_CUES)
    non_senior = non_senior or any(
        re.search(pattern, title_lower) for pattern in _NON_SENIORITY_CUES
    )
    if re.search(
        r"\b(?:senior|staff|principal|distinguished)[ -](?:level|role|position)\b"
        r"|\b(?:senior|staff|principal)\s+(?:software|backend|front[ -]?end|full[ -]?stack|"
        r"engineering|engineer|developer)\b",
        description.lower(),
    ):
        senior = True
    if re.search(
        r"\b(?:junior|entry[ -]level|graduate|mid[ -]level|early[ -]career)"
        r"\s+(?:role|position|engineer|developer|candidate)\b",
        description.lower(),
    ):
        non_senior = True

    # Lead is a senior indicator in role titles or explicit people leadership,
    # not when the description merely says to lead a project or task.
    if re.search(r"\b(?:lead|team lead|tech lead|technical lead)\b", title_lower) and not re.search(
        r"\blead generation\b", title_lower
    ):
        senior = True
    if re.search(
        r"\b(manage|managing|managed)\s+(?:a|the|our)?\s*(?:team|group|direct reports)\b"
        r"|\bdirect reports\b|\bpeople management\b|\blead(?:ing)?\s+(?:a|the|our)\s+"
        r"(?:team|group|engineering organization)\b",
        description.lower(),
    ):
        senior = True
    if re.search(r"\bmid[ -]senior\b", label_lower):
        senior = True

    years = _required_experience_years(text)
    if years is not None:
        low, high = years
        if low >= 7:
            senior = True
        elif high <= 3:
            non_senior = True

    if senior == non_senior:
        return "unknown"
    return "senior" if senior else "non_senior"


def _required_experience_years(text: str) -> tuple[int, int] | None:
    ranges = re.findall(
        r"\b(\d+)\s*(?:-|to)\s*(\d+)\s*\+?\s*years?\b", text.lower()
    )
    if ranges:
        return min(int(low) for low, _ in ranges), max(int(high) for _, high in ranges)
    matches = re.findall(
        r"\b(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+|relevant\s+|industry\s+)?experience\b",
        text.lower(),
    )
    at_least = re.findall(r"\bat least\s+(\d+)\s+years?\b", text.lower())
    values = [int(value) for value in matches + at_least]
    if not values:
        return None
    return min(values), max(values)


def classify_work_arrangement(item: Any) -> str:
    """Use structured work-mode fields first; unknown/contradictory text stays unknown."""
    raw = item.raw_payload or {}
    for key in (
        "workplaceType", "workplace_type", "workArrangement", "work_arrangement",
        "remoteStatus", "remote_status", "workplace",
    ):
        value = raw.get(key)
        classified = _normalize_work_arrangement(value)
        if classified:
            return classified
    classified = _normalize_work_arrangement(item.remote_status)
    if classified:
        return classified
    text = f"{item.title or ''} {item.description or ''} {item.location or ''}".lower()
    hybrid = bool(re.search(r"\bhybrid\b|\b\d+\s+days?\s+(?:in|at)\s+(?:the\s+)?office\b", text))
    remote = bool(re.search(r"\bremote\b|\bwork from home\b|\bwork-from-home\b", text))
    in_person = bool(re.search(r"\bon[ -]?site\b|\bin[ -]person\b|\boffice[ -]based\b", text))
    if hybrid:
        if re.search(r"\b(?:remote|hybrid|on[ -]?site|in[ -]person)\s+or\s+"
                     r"(?:remote|hybrid|on[ -]?site|in[ -]person)\b", text):
            return "unknown"
        return "hybrid"
    modes = [mode for mode, found in (("remote", remote), ("in_person", in_person)) if found]
    return modes[0] if len(modes) == 1 else "unknown"


def _normalize_work_arrangement(value: Any) -> str | None:
    text = re.sub(r"[_-]+", " ", str(value or "").lower()).strip()
    if not text:
        return None
    if re.search(r"\bhybrid\b", text):
        return "hybrid"
    if re.search(r"\bremote\b|work from home", text):
        return "remote"
    if re.search(r"\bon ?site\b|in person|office based", text):
        return "in_person"
    return None


def _continents_for_place(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list | tuple | set):
        regions: set[str] = set()
        for part in value:
            regions.update(_continents_for_place(part))
        return regions
    if isinstance(value, dict):
        return _continents_for_place(
            value.get("countryCode") or value.get("country_code") or value.get("country")
            or value.get("region") or value.get("location") or value.get("name")
        )
    source_text = str(value).strip()
    text = re.sub(r"[_-]+", " ", source_text.lower()).strip()
    if not text:
        return set()
    regions = {
        region
        for region in JOB_REGIONS
        if re.search(rf"\b{re.escape(region.lower())}\b", text)
    }
    code_tokens: set[str] = set()
    if re.fullmatch(r"[A-Za-z]{2}", source_text):
        code_tokens.add(source_text.upper())
    code_tokens.update(re.findall(r"(?:,|\(|\s-\s)\s*([A-Z]{2})\b", source_text))
    for region, codes in _CONTINENT_COUNTRY_CODES.items():
        if code_tokens & codes:
            regions.add(region)
        if any(
            re.search(rf"\b{re.escape(name)}\b", text)
            for name in _CONTINENT_COUNTRY_NAMES[region]
        ):
            regions.add(region)
        if any(
            re.search(rf"\b{re.escape(marker)}\b", text)
            for marker in _CITY_REGION_MARKERS[region]
        ):
            regions.add(region)
    if re.search(r"\bemea\b", text):
        regions.update(("Europe", "Africa", "Asia"))
    if re.search(r"\bworldwide\b|\bglobal(?:ly)?\b|\banywhere in the world\b", text):
        regions.update(JOB_REGIONS)
    return regions


def job_eligible_regions(item: Any, arrangement: str) -> set[str]:
    """Resolve actual job geography, never using employer name/headquarters."""
    raw = item.raw_payload or {}
    if arrangement == "remote":
        for key in (
            "eligibleCountries", "eligible_countries", "remoteCountries", "remote_countries",
            "workplaceCountries", "workplace_countries", "remoteLocations", "remote_locations",
            "workLocations", "work_locations", "locationRestrictions",
        ):
            if raw.get(key):
                return _continents_for_place(raw[key])
        explicit_remote = re.findall(
            r"\bremote\s+(?:from|in|across|throughout|within)\s+([A-Za-z][A-Za-z ,/&-]{1,50})",
            str(item.description or ""),
            flags=re.IGNORECASE,
        )
        for scope in explicit_remote:
            regions = _continents_for_place(scope)
            if regions:
                return regions
        location = str(item.location or "")
        if re.search(r"\bremote\b", location.lower()) and not _continents_for_place(location):
            return set()
        return _continents_for_place(item.country_code) or _continents_for_place(location)
    # On-site and hybrid roles are tied to their work site, which is the job
    # location field, not a company address mentioned in the description.
    return _continents_for_place(item.country_code) or _continents_for_place(item.location)


def matches_region_work_arrangements(
    item: Any,
    *,
    regions: list[str],
    work_arrangements: dict[str, list[str]],
) -> tuple[bool, str | None, str]:
    arrangement = classify_work_arrangement(item)
    if arrangement == "unknown":
        return False, None, arrangement
    eligible = job_eligible_regions(item, arrangement)
    for region in regions:
        if arrangement in work_arrangements.get(region, []) and region in eligible:
            return True, region, arrangement
    return False, None, arrangement

AGGREGATOR_HOSTS = (
    "linkedin.com",
    "indeed.com",
    "glassdoor.",
    "ziprecruiter.",
    "google.com",
    "monster.com",
)

ENGLISH_POSITIVE = [
    r"\benglish\b",
    r"fluent english",
    r"working language[:\s]+english",
    r"english (required|mandatory|fluent)",
]


def normalize_location_blob(*parts: str | None) -> str:
    return " ".join(p.strip().lower() for p in parts if p).strip()


def detect_country_code(location: str | None, description: str = "") -> str | None:
    blob = normalize_location_blob(location, description[:2000])
    if not blob:
        return None
    # Explicit country codes like ", NL" or "Netherlands"
    for name, code in sorted(EEA_NAME_TO_CODE.items(), key=lambda x: -len(x[0])):
        if name in blob:
            return code if code != "xx" else None
    for code, name in EEA_COUNTRIES.items():
        if re.search(rf"\b{code}\b", blob) or name.lower() in blob:
            return code
    return None


def is_eea_location(location: str | None, description: str = "") -> bool:
    code = detect_country_code(location, description)
    return code is not None and code in EEA_COUNTRIES


def is_europe_location(location: str | None, description: str = "") -> bool:
    if is_eea_location(location, description):
        return True
    blob = normalize_location_blob(location, description[:2000])
    if not blob:
        return False
    for name in sorted(EUROPE_EXTRA, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", blob):
            return True
    return bool(re.search(r"\buk\b", blob) and "ukraine" not in blob)


def normalize_regions(regions: list[str] | None) -> list[str]:
    """Keep known regions in display order. Default to Europe when none are chosen."""
    chosen = {str(region) for region in (regions or [])}
    ordered = [region for region in JOB_REGIONS if region in chosen]
    return ordered or ["Europe"]


def match_region(*parts: str | None, regions: list[str] | None = None) -> str | None:
    """Return the first selected region named by the posting."""
    blob = normalize_location_blob(*parts)
    if not blob:
        return None
    for region in normalize_regions(regions):
        if region == "Europe":
            if is_europe_location(blob):
                return region
            continue
        for marker in _REGION_MARKERS.get(region, ()):
            if re.search(rf"\b{re.escape(marker)}\b", blob):
                return region
    return None


def requires_non_english(description: str, title: str = "") -> bool:
    blob = f"{title}\n{description}".lower()
    return any(re.search(p, blob) for p in ADDITIONAL_LANGUAGE_PATTERNS)


def company_website_apply_url(*urls: str | None) -> str | None:
    for url in urls:
        if not url or not str(url).lower().startswith("http"):
            continue
        lower = str(url).lower()
        if any(host in lower for host in AGGREGATOR_HOSTS):
            continue
        return str(url)
    return None


def title_looks_senior(title: str, description: str = "") -> bool:
    t = f"{title} {description[:1500]}".lower()
    # Years requirement that implies senior
    years = re.search(r"(\d+)\+?\s*years?", t)
    if years and int(years.group(1)) >= 7:
        return True
    for pat in SENIOR_TITLE_PATTERNS:
        if re.search(pat, title.lower()):
            return True
    # Leadership expectations in JD with non-senior title still count
    return bool(
        re.search(r"manage(s|ing)?\s+(a\s+)?team|direct reports|people management", t)
        and not re.search(r"junior|associate|intern", title.lower())
    )


def title_looks_preferred_engineering(title: str) -> bool:
    t = title.lower()
    return any(re.search(p, t) for p in PREFERRED_TITLE_PATTERNS)


def visa_sponsorship_blocked(description: str) -> bool:
    d = description.lower()
    return any(re.search(p, d) for p in VISA_BLOCK_PATTERNS)


def english_required_or_implied(description: str, title: str = "") -> bool:
    blob = f"{title}\n{description}".lower()
    if any(re.search(p, blob) for p in ENGLISH_POSITIVE):
        return True
    # Many EEA eng postings are English-first without stating it; allow unknown as pass
    # Spec: require English as working language — if explicitly another language only, fail
    return not (
        re.search(
            r"dutch only|german only|french only|must speak (dutch|german|french|swedish)",
            blob,
        )
        and "english" not in blob
    )


def posted_within_hours(
    posted_at: datetime | None, hours: int = 24, *, now: datetime | None = None
) -> bool:
    if posted_at is None:
        return False
    now = now or datetime.now(UTC)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=UTC)
    return (now - posted_at) <= timedelta(hours=hours) and posted_at <= now + timedelta(minutes=5)


def applicant_count_ok(count: int | None, *, linkedin_source: bool) -> bool:
    """Require a verified count below 100, regardless of the source."""
    if count is None:
        return False
    return count < 100


def classify_visa_sponsorship(description: str) -> str:
    if visa_sponsorship_blocked(description):
        return "blocked"
    if re.search(
        r"visa sponsorship|work permit|relocation support|we sponsor", description.lower()
    ):
        return "available"
    return "unknown"
