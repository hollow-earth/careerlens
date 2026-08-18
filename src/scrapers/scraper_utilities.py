import re
import unicodedata

from tomllib import load
from typing_extensions import Any

with open("config.toml", "rb") as f:
    toml_config = load(f)

def normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )

term_blacklist = {normalize(term) for term in toml_config["search"]["blacklisted_terms"]}
excluded_pattern = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in term_blacklist) + r")\b")

company_blacklist = {normalize(company) for company in toml_config["search"]["blacklisted_companies"]}

def load_config() -> dict[str, Any]:
    return toml_config

def is_title_blacklisted(title: str) -> bool:
    return excluded_pattern.search(normalize(title)) is not None
        

def is_company_blacklisted(company: str) -> bool:
    return company.lower() in company_blacklist