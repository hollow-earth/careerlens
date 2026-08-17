from tomllib import load
from typing_extensions import Any
from sqlite3 import Connection

with open("config.toml", "rb") as f:
    toml_config = load(f)

company_blacklist = {company.lower() for company in toml_config["search"]["companies_to_skip"]}

def load_config() -> dict[str, Any]:
    return toml_config

def is_company_blacklisted(company: str) -> bool:
    return company in company_blacklist