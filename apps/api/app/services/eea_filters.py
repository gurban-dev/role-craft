"""EEA geography, seniority, visa, and English validation helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

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
    if re.search(r"\buk\b", blob) and "ukraine" not in blob:
        return True
    return False


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
    if re.search(r"manage(s|ing)?\s+(a\s+)?team|direct reports|people management", t):
        if not re.search(r"junior|associate|intern", title.lower()):
            return True
    return False


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
    if re.search(r"dutch only|german only|french only|must speak (dutch|german|french|swedish)", blob):
        if "english" not in blob:
            return False
    return True


def posted_within_hours(posted_at: datetime | None, hours: int = 24, *, now: datetime | None = None) -> bool:
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
    if re.search(r"visa sponsorship|work permit|relocation support|we sponsor", description.lower()):
        return "available"
    return "unknown"
