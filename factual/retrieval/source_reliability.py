"""Domain/type policy for estimating how much to trust a retrieved source.

Scores are spread across the three bands used by ``filter_sources``
(KEEP >= 0.75, DOWN_WEIGHT >= 0.45, REJECT below that):

    KEEP         0.97  government / official statistics
                 0.95  intergovernmental bodies
                 0.93  academic institutions
                 0.92  peer-reviewed publishers & scholarly indexes
                 0.90  curated reference works
                 0.88  standards & professional bodies
                 0.86  scholarly preprints
                 0.84  wire services & public broadcasters
                 0.82  reputable national newspapers
                 0.80  encyclopedic wiki (Wikipedia)
                 0.78  official vendor / project documentation
                 0.76  established non-profits & museums
    DOWN_WEIGHT  0.70  general news & magazines
                 0.62  educational / explainer sites
                 0.58  technical Q&A (Stack Exchange)
                 0.55  unknown .org / .net
                 0.52  unknown site (default)
                 0.48  blogs & self-publishing platforms
    REJECT       0.40  low-trust TLDs
                 0.38  forums & general Q&A
                 0.32  social media & video platforms
                 0.30  open user-edited wikis (fandom etc.)

Domain matches are exact or on a dot boundary, so ``bbc.co.uk`` matches
``news.bbc.co.uk`` but never ``notbbc.co.uk``.
"""

from __future__ import annotations

from typing import Any

# Weight for each source tier. ``source_type`` values produced elsewhere
# (``government``, ``academic``, ``news``, ``blog``, ``general`` ...) map here too.
SOURCE_RELIABILITY_WEIGHTS: dict[str, float] = {
    "government": 0.97,
    "intergovernmental": 0.95,
    "academic": 0.93,
    "scholarly_publisher": 0.92,
    "reference": 0.90,
    "standards_body": 0.88,
    "preprint": 0.86,
    "wire_news": 0.84,
    "reputable_news": 0.82,
    "encyclopedia_wiki": 0.80,
    "official_docs": 0.78,
    "institutional": 0.76,
    "news": 0.70,
    "educational": 0.62,
    "technical_qa": 0.58,
    "general_org": 0.55,
    "general": 0.52,
    "blog": 0.48,
    "low_trust_tld": 0.40,
    "forum": 0.38,
    "social": 0.32,
    "user_wiki": 0.30,
}

# Aliases for source_type labels other code may emit.
SOURCE_TYPE_ALIASES: dict[str, str] = {
    "gov": "government",
    "official": "government",
    "official_gov": "government",
    "intergov": "intergovernmental",
    "university": "academic",
    "edu": "academic",
    "journal": "scholarly_publisher",
    "encyclopedia": "reference",
    "wire": "wire_news",
    "documentation": "official_docs",
    "docs": "official_docs",
    "nonprofit": "institutional",
    "qa": "forum",
    "social_media": "social",
}

DEFAULT_RELIABILITY = SOURCE_RELIABILITY_WEIGHTS["general"]

# Registrable domains (and everything under them) per tier. Hosts under
# .gov/.edu/.int and ccTLD equivalents are handled by suffix rules below;
# a .edu listed here deliberately overrides "academic" (e.g. think tanks).
DOMAIN_TIERS: dict[str, tuple[str, ...]] = {
    "government": (
        "europa.eu", "gc.ca", "canada.ca", "gouv.fr", "bund.de", "admin.ch",
        "overheid.nl", "regjeringen.no",
    ),
    "intergovernmental": (
        "un.org", "unesco.org", "unicef.org", "worldbank.org", "imf.org",
        "oecd.org", "wto.org", "nato.int", "icrc.org", "iaea.org", "ipcc.ch",
    ),
    "academic": (
        "ox.ac.uk", "cam.ac.uk", "ethz.ch", "epfl.ch", "mpg.de", "cnrs.fr",
        "csiro.au", "riken.jp",
    ),
    "scholarly_publisher": (
        "nature.com", "science.org", "sciencedirect.com", "springer.com",
        "link.springer.com", "wiley.com", "onlinelibrary.wiley.com",
        "tandfonline.com", "sagepub.com", "jstor.org", "ieee.org",
        "ieeexplore.ieee.org", "acm.org", "dl.acm.org", "plos.org", "cell.com",
        "thelancet.com", "nejm.org", "bmj.com", "jamanetwork.com",
        "pnas.org", "oup.com", "academic.oup.com", "cambridge.org",
        "frontiersin.org", "mdpi.com", "aps.org", "acs.org", "rsc.org",
        "iop.org", "semanticscholar.org", "doi.org", "europepmc.org",
        "cochranelibrary.com", "aclanthology.org", "openreview.net",
        "proceedings.mlr.press", "neurips.cc", "jmlr.org",
    ),
    "reference": (
        "britannica.com", "oxfordreference.com", "merriam-webster.com",
        "dictionary.cambridge.org", "oed.com", "worldbook.com",
        "encyclopedia.com", "ebsco.com", "mathworld.wolfram.com",
        "wolframalpha.com", "ourworldindata.org", "statista.com", "history.com",
        "guinnessworldrecords.com", "nobelprize.org", "imdb.com",
    ),
    "standards_body": (
        "iso.org", "w3.org", "ietf.org", "rfc-editor.org", "unicode.org",
        "ecma-international.org", "asme.org", "ashrae.org", "iec.ch",
        "itu.int", "ansi.org", "ama-assn.org", "acponline.org",
        "heart.org", "cancer.org", "mayoclinic.org", "clevelandclinic.org",
        "hopkinsmedicine.org", "nhs.uk",
    ),
    "preprint": (
        "arxiv.org", "biorxiv.org", "medrxiv.org", "ssrn.com",
        "researchgate.net", "papers.nips.cc",
    ),
    "wire_news": (
        "reuters.com", "apnews.com", "afp.com", "bbc.co.uk", "bbc.com",
        "npr.org", "pbs.org", "abc.net.au", "cbc.ca", "dw.com",
        "france24.com", "nhk.or.jp", "rnz.co.nz",
    ),
    "reputable_news": (
        "nytimes.com", "washingtonpost.com", "theguardian.com", "wsj.com",
        "ft.com", "economist.com", "bloomberg.com", "theatlantic.com",
        "newyorker.com", "latimes.com", "theglobeandmail.com", "thehindu.com",
        "indianexpress.com", "scmp.com", "aljazeera.com", "lemonde.fr",
        "spiegel.de", "smh.com.au", "scientificamerican.com",
        "newscientist.com", "technologyreview.com",
    ),
    "encyclopedia_wiki": ("wikipedia.org", "wikimedia.org", "wikidata.org"),
    "official_docs": (
        "docs.python.org", "python.org", "developer.mozilla.org",
        "learn.microsoft.com", "docs.microsoft.com", "developer.apple.com",
        "developer.android.com", "cloud.google.com", "developers.google.com",
        "ai.google.dev", "docs.aws.amazon.com", "aws.amazon.com",
        "developer.nvidia.com", "docs.nvidia.com", "ibm.com", "oracle.com",
        "docs.oracle.com", "pytorch.org", "tensorflow.org", "keras.io",
        "scikit-learn.org", "numpy.org", "pandas.pydata.org", "react.dev",
        "nodejs.org", "rust-lang.org", "go.dev", "kubernetes.io",
        "docker.com", "postgresql.org", "mysql.com", "linux.org",
        "kernel.org", "gnu.org", "huggingface.co", "openai.com",
        "anthropic.com", "deepmind.google", "research.google",
    ),
    "institutional": (
        "smithsonianmag.com", "si.edu", "nationalgeographic.com",
        "metmuseum.org", "britishmuseum.org", "amnh.org", "khanacademy.org",
        "pewresearch.org", "brookings.edu", "rand.org", "carnegieendowment.org",
        "amnesty.org", "hrw.org", "redcross.org", "wwf.org", "iucn.org",
        "audubon.org", "exploratorium.edu",
    ),
    "news": (
        "cnn.com", "nbcnews.com", "cbsnews.com", "abcnews.go.com", "usatoday.com",
        "time.com", "newsweek.com", "forbes.com", "businessinsider.com",
        "cnbc.com", "vox.com", "axios.com", "politico.com", "thehill.com",
        "independent.co.uk", "telegraph.co.uk", "skynews.com", "ndtv.com",
        "hindustantimes.com", "timesofindia.indiatimes.com", "wired.com",
        "arstechnica.com", "theverge.com", "techcrunch.com", "zdnet.com",
        "livescience.com", "space.com", "sciencedaily.com", "phys.org",
    ),
    "educational": (
        "investopedia.com", "howstuffworks.com", "worldatlas.com",
        "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com",
        "towardsdatascience.com", "machinelearningmastery.com",
        "simplilearn.com", "datacamp.com", "coursera.org", "edx.org",
        "byjus.com", "chem.libretexts.org", "libretexts.org",
        "sparknotes.com", "cliffsnotes.com", "study.com", "thoughtco.com",
        "verywellhealth.com", "healthline.com", "webmd.com",
        "medicalnewstoday.com", "infoplease.com", "factmonster.com",
        "countryreports.org", "nationsonline.org",
    ),
    "technical_qa": (
        "stackoverflow.com", "stackexchange.com", "superuser.com",
        "serverfault.com", "askubuntu.com", "mathoverflow.net",
        "github.com", "gitlab.com",
    ),
    "blog": (
        "medium.com", "substack.com", "blogspot.com", "wordpress.com",
        "tumblr.com", "wixsite.com", "weebly.com", "hashnode.dev",
        "dev.to", "ghost.io", "squarespace.com", "linkedin.com",
    ),
    "forum": (
        "reddit.com", "quora.com", "answers.com", "answers.yahoo.com",
        "ask.com", "chegg.com", "brainly.com", "brainly.in", "coursehero.com",
        "4chan.org", "boards.ie",
    ),
    "social": (
        "twitter.com", "x.com", "facebook.com", "instagram.com",
        "tiktok.com", "youtube.com", "youtu.be", "pinterest.com",
        "threads.net", "snapchat.com", "telegram.org", "t.me",
    ),
    "user_wiki": ("fandom.com", "wikia.com", "wikihow.com", "everybodywiki.com"),
}

# Second-level labels that mark government / academic hosts under a ccTLD,
# e.g. gov.uk, gov.in, gouv.fr, gob.mx, go.jp, ac.uk, edu.au.
_GOV_SECOND_LEVEL = {"gov", "govt", "gouv", "gob", "go", "gv", "mil", "nic"}
_ACADEMIC_SECOND_LEVEL = {"ac", "edu", "uni"}
_GOV_TLDS = {"gov", "mil"}
_INTERGOV_TLDS = {"int"}
_ACADEMIC_TLDS = {"edu"}
_LOW_TRUST_TLDS = {
    "xyz", "top", "click", "buzz", "info", "biz", "loan", "work", "gq",
    "tk", "ml", "cf", "ga", "rest", "fit", "icu", "cyou", "monster",
}
_ORG_TLDS = {"org", "net"}

# Precedence when a host matches several tiers: the more specific
# (longest) matching domain wins, so build one lookup sorted by length.
_DOMAIN_LOOKUP: list[tuple[str, str]] = sorted(
    ((domain, tier) for tier, domains in DOMAIN_TIERS.items() for domain in domains),
    key=lambda item: len(item[0]),
    reverse=True,
)


def _normalize_host(domain: str) -> str:
    host = domain.strip().lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0].split(":", 1)[0].rstrip(".")
    return host.removeprefix("www.")


def _matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _tier_from_domain(host: str) -> str | None:
    if not host:
        return None
    for domain, tier in _DOMAIN_LOOKUP:
        if _matches(host, domain):
            return tier

    labels = host.split(".")
    tld = labels[-1]
    second = labels[-2] if len(labels) >= 2 else ""
    is_cc_tld = len(tld) == 2

    if tld in _GOV_TLDS or (is_cc_tld and second in _GOV_SECOND_LEVEL):
        return "government"
    if tld in _INTERGOV_TLDS:
        return "intergovernmental"
    if tld in _ACADEMIC_TLDS or (is_cc_tld and second in _ACADEMIC_SECOND_LEVEL):
        return "academic"
    if labels[0] == "blog" or labels[0].startswith("blog-"):
        return "blog"
    if tld in _LOW_TRUST_TLDS:
        return "low_trust_tld"
    if tld in _ORG_TLDS:
        return "general_org"
    return None


def _tier_from_type(source_type: str) -> str | None:
    source_type = source_type.strip().lower()
    source_type = SOURCE_TYPE_ALIASES.get(source_type, source_type)
    if source_type in SOURCE_RELIABILITY_WEIGHTS and source_type != "general":
        return source_type
    return None


def classify_source(source: dict[str, Any]) -> tuple[str, float]:
    """Return the reliability tier name and its score for a source.

    A known domain is the most specific signal, so it wins. Otherwise an
    explicit ``source_type`` is used, and anything left is ``general``.
    """
    host = _normalize_host(str(source.get("domain") or source.get("url") or ""))
    source_type = str(source.get("source_type") or "general")

    domain_tier = _tier_from_domain(host)
    type_tier = _tier_from_type(source_type)

    if domain_tier in {"general_org", "low_trust_tld"} and type_tier:
        # A TLD-only guess is weaker than a type assigned upstream.
        tier = type_tier
    else:
        tier = domain_tier or type_tier or "general"

    # Self-published content never outranks a blog, whatever the host.
    blog_score = SOURCE_RELIABILITY_WEIGHTS["blog"]
    if "blog" in source_type.lower() and SOURCE_RELIABILITY_WEIGHTS[tier] > blog_score:
        tier = "blog"

    return tier, SOURCE_RELIABILITY_WEIGHTS[tier]


def estimate_source_reliability(source: dict[str, Any]) -> float:
    return classify_source(source)[1]
