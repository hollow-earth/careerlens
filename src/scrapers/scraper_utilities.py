from tomllib import load

with open("config.toml", "rb") as f:
    toml_config = load(f)

company_blacklist = set(toml_config["search"]["companies_to_skip"])

def is_company_blacklisted(company: str) -> bool:
    return company in company_blacklist