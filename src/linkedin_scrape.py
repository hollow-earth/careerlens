import tomllib
from bs4 import BeautifulSoup
import playwright
import re
from playwright.sync_api import Page, expect, sync_playwright



# Load config and throw everything into a searcj query
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

keywords = " OR ".join(f'"{item}"' for item in config["search"]["keywords"])
location = config["search"]["locations"]
time_filter = str(config["search"]["time_filter"])
distance = str(config["search"]["distance"])

search_url = "https://www.linkedin.com/jobs/search?"
if keywords:
    search_url += f"keywords={keywords}&"
if location:
    search_url += f"location={location}&"
if time_filter:
    search_url += f"f_TPR=r{time_filter}&"
if distance:
    search_url += f"distance={distance}&"
if search_url == "https://www.linkedin.com/jobs/search?":
    raise Exception("You need at least one search term for LinkedIn!")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(search_url)
    
    # Close the annoying pop ups
    page.get_by_role("button", name="Dismiss").click()
    page.get_by_role("button", name="Reject").click()

    browser.close()

get_started = page.get_by_role("link", name="Get started")