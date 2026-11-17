"""Clean and classify the job-postings snapshot (data/raw/postings/*.csv.gz).

Every posting gets:
  family       job family, from the title (Data & analytics, Software engineering, ...)
  eng_type     for engineering titles, the kind of engineer (Software, Mechanical, ...)
  seniority    Internship / Entry level / Mid or not stated / Senior & management
  loc_bucket   Los Angeles area / Other California / Other U.S. / Remote (U.S.) / Outside U.S. / Not stated
  title_norm   the title with seniority words and qualifiers removed, for counting common roles

The rules are keyword rules written by hand. They are checked in tests/test_postings.py
and their limits are listed in the README.
"""
import re

import pandas as pd

SECTORS = {
    "T": "Technology & software",
    "H": "Health care & life sciences",
    "F": "Finance, insurance & real estate",
    "A": "Aerospace, defense & hardware",
    "M": "Media, entertainment & gaming",
    "C": "Consumer, retail & logistics",
    "R": "Various (remote job boards)",
}

# Board slugs that turned out to belong to a different organisation than intended,
# and companies found on two platforms (the smaller copy is dropped).
DROP_BOARDS = {
    ("greenhouse", "archer"), ("greenhouse", "tubi"), ("greenhouse", "ramp"),
    ("ashby", "radiant"), ("ashby", "neon"), ("ashby", "cedar"),
}
FIX_BOARDS = {
    ("greenhouse", "xai"): ("xAI (SpaceX)", "T"),
    ("greenhouse", "intercom"): ("Fin (Intercom)", "T"),
    ("ashby", "found"): ("Found", "F"),
    ("ashby", "flock"): ("Flock (UK insurtech)", "F"),
    ("ashby", "atomic"): ("Atomic (venture studio)", "T"),
    ("ashby", "fable"): ("Fable", "T"),
}
BOARD_SOURCES = {"remotive", "remoteok", "jobicy"}

FAMILIES = [
    ("Internship", r"\bintern\b|\binternship|\bco-?op\b|summer analyst|summer associate"),
    ("Data & analytics", r"data analy|analytics|business intelligence|\bbi\b|data scien|data engineer|analytics engineer"
                         r"|insights? (analyst|manager|lead)|reporting analyst|statistician|decision scien|business analyst"
                         r"|data (specialist|manager|lead|architect|platform|strategy)|\bdata\b.*\banalyst\b"),
    ("AI & machine learning", r"machine learning|\bml\b|\bai\b|deep learning|\bllm|applied scien|research engineer"
                              r"|research scientist|computer vision|\bnlp\b|inference|post-training|pre-training|model behavior|researcher"),
    ("Product & design", r"product manager|product owner|product lead|head of product|product director|designer|\bux\b|\bui\b"
                         r"|user research|design (lead|manager|director)|product design|product operations|technical program manager"),
    ("Health care (clinical)", r"\bnurse|\brn\b|\blpn\b|\blvn\b|\bnp\b|physician|\bmd\b|doctor|clinician|therapist|counselor"
                               r"|psychiatr|psycholog|pharmacist|pharmacy tech|medical assistant|care (coordinator|manager|navigator)"
                               r"|health coach|dietitian|dentist|hygienist|phlebotom|radiolog|sonograph|social worker|\blcsw\b"
                               r"|\bbcba\b|behavior technician|caregiver|medical director|patient care|clinical (lead|specialist|supervisor)"),
    ("Science & research", r"scientist|research associate|biolog|chemist|laborator|\blab\b|assay|bioinformatic|clinical research"
                           r"|regulatory|genomic|translational|pharmacolog|toxicolog|formulation|process development"),
    ("Software engineering & IT", r"software|developer|programmer|system administrator|systems administrator|sysadmin"
                             r"|\bit (support|specialist|manager|administrator|analyst)|help ?desk|cyber|security (architect|analyst|operations)"
                             r"|security incident|\bsoc\b|penetration|threat|\bswe\b|front.?end|back.?end|full.?stack|mobile engineer|\bios\b|android"
                             r"|devops|site reliability|\bsre\b|platform engineer|infrastructure engineer|security engineer"
                             r"|cloud engineer|product engineer|forward deployed engineer|engineering manager|qa engineer"
                             r"|test automation|web engineer|database engineer|tech lead|member of technical staff"
                             r"|detection engineer|network engineer|it engineer|solutions architect|production engineer"),
    ("Finance & accounting", r"account(ant|ing)|finance|financial|fp&a|controller|\btax\b|treasury|audit|payroll|billing"
                             r"|accounts (payable|receivable)|trader|trading|\bquant|investment|portfolio|underwrit|actuar"
                             r"|credit|wealth advisor|bookkeep|risk analyst|capital markets|banker"),
    ("Sales & customer success", r"account executive|\bsales\b|business development|\bbdr\b|\bsdr\b|account manager"
                                 r"|customer success|solutions engineer|sales engineer|customer engineer|support engineer"
                                 r"|partnership|customer support|support (specialist|representative|agent)|customer experience"
                                 r"|client (services|success)|account director|deployment strategist|go.to.market|\bgtm\b"
                                 r"|implementation|onboarding|representative|commercial|client partner|account lead"),
    ("Marketing & communications", r"marketing|brand|content|communications|\bpr\b|public relations|social media|\bseo\b"
                                   r"|growth|copywrit|community|\bevents?\b|demand gen|campaign|lifecycle|influencer|editorial"),
    ("Creative & media production", r"producer|editor|writer|animator|artist|art director|video|motion graphic|game designer"
                                    r"|level designer|sound|audio|cinematograph|photograph|creative|illustrat|narrative|\bvfx\b"
                                    r"|\b3d\b|technical artist|journalist|reporter|composer|director of photography"),
    ("People, legal & admin", r"recruit|talent|\bhr\b|human resources|people (partner|operations|business|ops|team)|legal"
                              r"|counsel|attorney|paralegal|compliance|executive assistant|administrative|office manager"
                              r"|receptionist|workplace|privacy|policy|government affairs"),
    ("Hardware & other engineering", r"mechanical|electrical|avionic|propulsion|manufacturing engineer|test engineer|structur"
                                     r"|systems engineer|\brf\b|firmware|embedded|hardware|materials|chemical engineer|civil"
                                     r"|process engineer|quality engineer|reliability engineer|controls|robotic|\bgnc\b|thermal"
                                     r"|design engineer|integration engineer|power|nuclear|optical|asic|fpga|silicon|battery"
                                     r"|aerospace|field engineer|manufacturing|machin|weld|composite"),
    ("Operations, service & supply chain", r"trainer|instructor|coach|stylist|esthetician|massage|front desk|detailer"
                                  r"|concierge|housekeep|attendant|cashier|cook|chef|server\b|operations|logistics|supply chain|warehouse|fulfillment|procurement|purchasing|inventory"
                                  r"|facilit|technician|assembl|operator|driver|courier|program manager|project manager"
                                  r"|planner|buyer|store|retail|general manager|restaurant|barista|crew|team member|inspector"
                                  r"|production|mechanic|maintenance|electrician|security officer|associate|specialist"
                                  r"|coordinator|manager|strategy|chief of staff|analyst"),
]
FAMILY_RE = [(name, re.compile(rx, re.I)) for name, rx in FAMILIES]

ENG_TYPES = [
    ("Software", r"software|front.?end|back.?end|full.?stack|mobile|\bios\b|android|web|platform|product engineer|forward deployed|member of technical staff"),
    ("Machine learning / AI", r"machine learning|\bml\b|\bai\b|research engineer|inference|deep learning|\bllm"),
    ("Data", r"data engineer|analytics engineer|data platform|database"),
    ("Security", r"security|detection"),
    ("Infrastructure, cloud & reliability", r"infrastructure|site reliability|\bsre\b|devops|cloud|network|systems engineer, infra|production engineer"),
    ("Sales & solutions", r"solutions|sales engineer|customer engineer|support engineer|field engineer|implementation"),
    ("Mechanical", r"mechanical|structur|thermal|propulsion|fluids"),
    ("Electrical & electronics", r"electrical|electronics|\brf\b|power|avionic|antenna|pcb"),
    ("Hardware, chips & embedded", r"hardware|asic|fpga|silicon|embedded|firmware|chip|verification"),
    ("Manufacturing, quality & test", r"manufactur|quality|test|process|production|industrial|reliability"),
    ("Systems & integration", r"systems|integration|\bgnc\b|guidance|controls"),
    ("Robotics & autonomy", r"robot|autonom|perception|motion planning|localization"),
    ("Civil, construction & facilities", r"civil|construction|facilities|structural|building"),
    ("Other engineering", r"engineer"),
]
ENG_RE = [(n, re.compile(rx, re.I)) for n, rx in ENG_TYPES]

INTERN_RE = re.compile(r"\bintern\b|\binternship|\bco-?op\b|summer (analyst|associate)", re.I)
ENTRY_RE = re.compile(r"\bjunior\b|\bjr\.?\b|entry|new grad|graduate|early career|apprentice|trainee|\bcampus\b|university"
                      r"|\bassociate\b(?! (director|general counsel|vice|vp|principal|partner))|\b(i|1)\b(?!\s*[-&])$"
                      r"|\b(i|1)\s*[,(/-]|level 1|\bl1\b", re.I)
SENIOR_RE = re.compile(r"\bsenior\b|\bsr\.?\b|\bstaff\b|principal|\blead\b|director|\bhead\b|\bvp\b|vice president"
                       r"|\bchief\b|distinguished|architect|\bii\b|\biii\b|\biv\b|\b[2-5]\b(?!\d)|expert|managing partner"
                       r"|supervisor|founding|executive director|\bsvp\b|\bevp\b", re.I)

LA_CITIES = ("los angeles|santa monica|culver city|el segundo|long beach|hawthorne|torrance|burbank|pasadena|glendale|irvine"
             "|costa mesa|anaheim|newport beach|huntington beach|santa ana|fullerton|tustin|lake forest|mission viejo"
             "|playa vista|venice|marina del rey|west hollywood|hollywood|beverly hills|carson|gardena|inglewood|redondo"
             "|manhattan beach|van nuys|north hollywood|chatsworth|valencia|santa clarita|downey|el monte|city of industry"
             "|compton|commerce|vernon|lakewood|cerritos|pomona|west covina|brea|orange, ca|aliso viejo|foothill ranch"
             "|rancho santa margarita|sylmar|calabasas|thousand oaks|westlake village|woodland hills|seal beach|cypress")
CA_CITIES = (r"california|,\s*ca\b|\bca,|san francisco|san jose|palo alto|mountain view|sunnyvale|menlo park|redwood city"
             r"|san mateo|oakland|berkeley|santa clara|san diego|sacramento|fremont|emeryville|foster city|south san francisco"
             r"|carlsbad|santa barbara|goleta|fresno|riverside|ontario, ca|san carlos|burlingame|milpitas|cupertino|los gatos"
             r"|pleasanton|livermore|walnut creek|san ramon|brisbane|hayward|alameda|novato|petaluma|santa cruz|bay area"
             r"|silicon valley|mojave|vandenberg|san luis obispo|ventura|oxnard|camarillo|bakersfield|stockton|modesto")
US_HINTS = (r"united states|\busa\b|\bu\.s\.|\bus\b|\bamer\b|namer|north america|nationwide"
            r"|,\s*(al|ak|az|ar|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok"
            r"|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b"
            r"|alabama|alaska|arizona|arkansas|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana"
            r"|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana"
            r"|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon"
            r"|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington"
            r"|wisconsin|wyoming|nyc|seattle|boston|austin|chicago|denver|atlanta|miami|dallas|houston|philadelphia"
            r"|pittsburgh|portland|salt lake|phoenix|minneapolis|detroit|nashville|raleigh|durham|columbus|brooklyn"
            r"|cambridge, ma|bellevue|redmond|kirkland|boulder|arlington|reston|herndon|mclean|bethesda|baltimore|tampa"
            r"|orlando|charlotte|st\. louis|kansas city|las vegas|san antonio|huntsville|cape canaveral|memphis|cincinnati")
ABROAD = (r"canada|toronto|vancouver|montreal|ottawa|calgary|london|england|\buk\b|united kingdom|ireland|dublin|germany|berlin"
          r"|munich|france|paris|netherlands|amsterdam|spain|madrid|barcelona|portugal|lisbon|poland|warsaw|krakow|india"
          r"|bengaluru|bangalore|hyderabad|mumbai|gurugram|gurgaon|pune|chennai|delhi|singapore|japan|tokyo|korea|seoul"
          r"|australia|sydney|melbourne|brazil|s[aã]o paulo|mexico|israel|tel aviv|sweden|stockholm|switzerland|zurich"
          r"|denmark|copenhagen|norway|oslo|finland|helsinki|italy|milan|rome|romania|bucharest|czech|prague|hungary"
          r"|budapest|\buae\b|dubai|abu dhabi|philippines|manila|china|shanghai|beijing|shenzhen|hong kong|taiwan|taipei"
          r"|argentina|buenos aires|colombia|bogot|chile|santiago|costa rica|\bemea\b|\bapac\b|latam|europe|asia|belgium"
          r"|brussels|austria|vienna|estonia|tallinn|ukraine|kyiv|serbia|belgrade|turkey|istanbul|south africa|cape town"
          r"|nigeria|lagos|kenya|nairobi|egypt|cairo|vietnam|thailand|bangkok|indonesia|jakarta|malaysia|kuala lumpur"
          r"|new zealand|auckland|greece|athens|luxembourg|scotland|edinburgh|glasgow|wales|belfast|gloucestershire"
          r"|bristol|manchester|reading, uk|riyadh|saudi|qatar|doha|peru|lima|uruguay|guatemala|puerto rico|king abdullah"
          r"|kuwait|ivoire|abidjan|slovenia|ljubljana|malm[oö]|gothenburg|croatia|zagreb|lithuania|vilnius|latvia|riga"
          r"|bulgaria|sofia|slovakia|bratislava|pakistan|karachi|lahore|bangladesh|dhaka|sri lanka|nepal|morocco|ghana"
          r"|\bind\b|mohali|noida|kochi|ahmedabad|cebu|ho chi minh|hanoi|osaka|kyoto|busan|perth|brisbane|adelaide"
          r"|wellington|hamburg|frankfurt|cologne|stuttgart|lyon|marseille|rotterdam|utrecht|eindhoven|antwerp|geneva"
          r"|basel|lausanne|valencia, spain|seville|porto|krak[oó]w|wroc|gda|pozna|cluj|iasi|tbilisi|yerevan|almaty")
LA_RE, CA_RE, US_RE, ABROAD_RE = (re.compile(x, re.I) for x in (LA_CITIES, CA_CITIES, US_HINTS, ABROAD))
REMOTE_RE = re.compile(r"remote|anywhere|work from home|distributed|virtual", re.I)
US_COUNTRY = {"us", "usa", "united states", "united states of america", "u.s."}

TITLE_STRIP = re.compile(r"\b(senior|sr\.?|junior|jr\.?|staff|principal|entry[- ]level|new grad|i{1,3}|iv|level \d|l\d)\b", re.I)
GENERIC_HEAD = re.compile(r"^(manager|director|head|lead|specialist|associate|analyst|engineer|coordinator|fellow|operations"
                          r"|senior manager|senior director|program manager|product manager|technician|consultant|partner)$", re.I)


HARDWARE_SECTORS = {"A"}


def family_of(title: str, sector: str = "") -> str:
    for name, rx in FAMILY_RE:
        if rx.search(title):
            if name == "Data & analytics" and re.search(r"software engineer|engineering manager|product manager|program manager", title, re.I) \
                    and not re.search(r"data engineer|analytics engineer|data scien|data analyst", title, re.I):
                continue
            if name == "AI & machine learning" and sector == "H" and re.search(r"scientist|researcher", title, re.I) \
                    and not re.search(r"machine learning|\bml\b|\bai\b|computer vision|\bllm", title, re.I):
                return "Science & research"
            if name == "Operations, service & supply chain" and re.search(r"engineer", title, re.I):
                break
            return name
    # A plain "Engineer" title: software at a software company, hardware at a hardware company.
    if re.search(r"engineer", title, re.I):
        return "Hardware & other engineering" if sector in HARDWARE_SECTORS else "Software engineering & IT"
    return "Other"


def eng_type_of(title: str) -> str:
    if not re.search(r"engineer|developer", title, re.I):
        return ""
    if re.search(r"developer", title, re.I) and not re.search(r"engineer", title, re.I):
        return "Software" if not re.search(r"business developer|sales", title, re.I) else ""
    for name, rx in ENG_RE:
        if rx.search(title):
            return name
    return "Other engineering"


IC_MANAGER = re.compile(r"(account|customer success|success|community|office|case|care|social media|channel|territory"
                        r"|partner|key account|relationship|store|shift|restaurant|property|content|event) manager", re.I)


def seniority_of(title: str, level: str = "") -> str:
    lv = (level or "").lower()
    if INTERN_RE.search(title) or "intern" in lv:
        return "Internship"
    if SENIOR_RE.search(title) or lv in {"senior", "mid-senior level", "director", "executive"}:
        return "Senior & management"
    if ENTRY_RE.search(title) or lv in {"entry level", "entry-level", "junior", "associate"}:
        return "Entry level"
    if re.search(r"manager", IC_MANAGER.sub(" ", title), re.I) or lv in {"manager"}:
        return "Senior & management"
    return "Mid or not stated"


STATE_ABBR = re.compile(r",\s*(al|ak|az|ar|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc"
                        r"|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b", re.I)


STATE_END = re.compile(r"\s(AL|AK|AZ|AR|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND"
                       r"|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)(\s|$)")


def location_of(loc: str, extra: str, remote: str, country: str) -> dict:
    """Bucket a posting's location. Several locations: the one nearest Los Angeles wins."""
    text = f"{loc} | {extra}".strip(" |")
    c = (country or "").strip().lower()
    abroad = bool(ABROAD_RE.search(text))
    us_strong = bool(US_RE.search(STATE_ABBR.sub(" ", text))) or c in US_COUNTRY
    us_abbr = (bool(STATE_ABBR.search(text)) or bool(STATE_END.search(text))) and not abroad
    is_la = bool(LA_RE.search(text))
    is_ca = is_la or bool(re.search(CA_CITIES.replace(r"|,\s*ca\b|\bca,", ""), text, re.I)) \
        or (bool(re.search(r",\s*ca\b|\bca,", text, re.I)) and not re.search(r"canada|toronto|vancouver|montreal", text, re.I))
    is_us = is_ca or us_strong or us_abbr
    is_remote = bool(REMOTE_RE.search(text)) or str(remote).strip().lower() in {"1", "true", "remote"}
    has_city = bool(STATE_ABBR.search(text)) or bool(re.search(r"new york|nyc|seattle|boston|austin|chicago|denver|atlanta"
                                                             r"|miami|dallas|houston|washington, d|brooklyn|philadelphia", text, re.I))
    if is_la:
        bucket = "Los Angeles area"
    elif is_ca:
        bucket = "Other California"
    elif is_us:
        bucket = "Remote (U.S.)" if is_remote and not has_city else "Other U.S."
    elif abroad or (c and c not in US_COUNTRY):
        bucket = "Outside U.S."
    elif is_remote:
        bucket = "Remote (country not stated)"
    else:
        bucket = "Not stated"
    return {"loc_bucket": bucket, "is_la": int(is_la), "is_ca": int(is_ca), "is_us": int(is_us), "is_remote": int(is_remote)}


def norm_title(title: str) -> str:
    parts = [p for p in re.split(r"\s[-–—|(]\s?|,\s|\s/\s", title) if p.strip()]
    t = parts[0] if parts else title
    head = re.sub(r"\s+", " ", TITLE_STRIP.sub(" ", t)).strip()
    if GENERIC_HEAD.match(head) and len(parts) > 1:  # "Manager, Finance" is more useful than "Manager"
        t = t + ", " + parts[1]
    t = TITLE_STRIP.sub(" ", t)
    t = re.sub(r"[^A-Za-z&+, ]", " ", t).strip(" ,")
    t = re.sub(r"\s+", " ", t).strip()
    return t.title() if t else title.strip().title()


def clean(raw: pd.DataFrame, snapshot_date: str) -> pd.DataFrame:
    df = raw.drop_duplicates(["source", "slug", "job_id"]).copy()
    df = df[~df.apply(lambda r: (r["source"], r["slug"]) in DROP_BOARDS, axis=1)]
    for (src, slug), (name, sec) in FIX_BOARDS.items():
        m = (df["source"] == src) & (df["slug"] == slug)
        df.loc[m, ["company", "sector"]] = [name, sec]
    # Postings on the remote job boards from a company we already have from its own careers page are duplicates.
    ats_companies = set(df.loc[~df["source"].isin(BOARD_SOURCES), "company"].str.lower())
    df = df[~(df["source"].isin(BOARD_SOURCES) & df["company"].str.lower().isin(ats_companies))]
    df["title"] = df["title"].str.replace(r"\s+", " ", regex=True).str.strip()
    df["sector_name"] = df["sector"].map(SECTORS)
    df["family"] = [family_of(ti, s) for ti, s in zip(df["title"], df["sector"])]
    df["eng_type"] = df["title"].map(eng_type_of)
    df["seniority"] = [seniority_of(t, lv) for t, lv in zip(df["title"], df["experience_level"])]
    df.loc[df["family"] == "Internship", "seniority"] = "Internship"
    # An internship keeps its subject: re-classify it without the word "intern".
    intern = df["family"] == "Internship"
    df.loc[intern, "family"] = [family_of(ti, s) for ti, s in zip(
        df.loc[intern, "title"].str.replace(INTERN_RE, " ", regex=True), df.loc[intern, "sector"])]
    loc = pd.DataFrame([location_of(*a) for a in zip(df["location"], df["location_extra"], df["remote"], df["country"])],
                       index=df.index)
    df = pd.concat([df, loc], axis=1)
    df["is_data_analyst"] = df["title"].str.contains(
        r"(?:data analyst|analytics analyst|business intelligence analyst|\bbi analyst|reporting analyst|business analyst"
        r"|data & analytics analyst|insights analyst|product analyst|marketing analyst|operations analyst"
        r"|analyst, (?:data|analytics|business|product|marketing|operations))", case=False, regex=True).astype(int)
    df["title_norm"] = df["title"].map(norm_title)
    posted = pd.to_datetime(df["posted_at"], errors="coerce", utc=True, format="mixed")
    df["posted_date"] = posted.dt.strftime("%Y-%m-%d")
    df["days_old"] = (pd.Timestamp(snapshot_date, tz="UTC") - posted).dt.days
    df["snapshot_date"] = snapshot_date
    for c in ("pay_min", "pay_max"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.reset_index(drop=True)
    df.insert(0, "posting_id", range(1, len(df) + 1))
    return df


def skills_long(df: pd.DataFrame) -> pd.DataFrame:
    s = df.loc[df["desc_fetched"].astype(str) == "1", ["posting_id", "skills"]].copy()
    s["skill"] = s["skills"].str.split("|")
    s = s.explode("skill")
    return s[s["skill"].fillna("") != ""][["posting_id", "skill"]].reset_index(drop=True)
