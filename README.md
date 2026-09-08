# CareerLens
A privacy-focused, local-first, AI-powered job search and recommendation engine that finds job postings, filters out irrelevant opportunities, evaluates them against your career goals and resume, and tells you which ones are actually worth applying to.

The goal is simple: spend less time looking for jobs and more time applying to the right ones.

<img width="1660" height="1270" alt="image" src="https://github.com/user-attachments/assets/c4aff75a-dc1d-4758-a874-8ae8d78e4495" />
<img width="1660" height="1270" alt="image" src="https://github.com/user-attachments/assets/6f4d5f02-f328-4572-855b-c89747f978da" />

## Project Status

CareerLens is a working personal prototype. It is actively usable, but some features and internal components are still being refined.

## How To Run
```bash
git clone https://github.com/hollow-earth/careerlens.git
cd careerlens

python -m venv .venv

# Bash / Zsh
source .venv/bin/activate

# Fish
source .venv/bin/activate.fish


python -m pip install -r requirements.txt
python src/main.py
```

## Requirements
- Python 3.14 (tested; other versions may work but are untested)
- Ollama for local LLM evaluation
- Playwright
**Ollama and Playwright must be installed and configured before running CareerLens.**

Playwright also requires the appropriate browser binaries to be installed. For example:

python -m playwright install firefox

### LLM Requirements
The default configuration uses a local LLM through Ollama. The model is configurable, so hardware requirements and performance will vary depending on the model selected.

I have had particularly good results with `hf.co/unsloth/Qwen3.8-27B-GGUF:UD-Q3_K_XL`, although this model is relatively demanding and requires a GPU with approximately 16 GB of VRAM. Due to a current issue with Ollama's Hugging Face model integration, installing this model may require additional manual steps. It is therefore not the default configuration.

On my system, using an AMD Radeon RX 9070 XT (16 GB VRAM), a single job entry takes approximately 15 seconds to process.

Each evaluation can involve a substantial amount of context. With three resumes and one job posting, approximately 8,000 tokens may be processed per evaluation. CareerLens currently allows up to 16,000 tokens of context to provide some headroom for larger inputs.

A smaller model can be used if the default configuration is too demanding for your hardware. Performance and recommendation quality will vary depending on the model selected.

## What It does
CareerLens automates much of the tedious work involved in a modern job search:

- Scrapes job postings from supported job sources
- Filters jobs using configurable keywords and company blacklists
- Deduplicates and normalizes job postings
- Stores job data locally using SQLite
- Evaluates jobs with a local LLM against your resume, skills, career goals, and preferences
- Scores opportunities from 0–100
- Provides a short recommendation and reasoning explaining why a job is or isn't a good fit
- Prioritizes applications so you can focus your time where it matters

Instead of giving you hundreds of job postings to sift through, CareerLens aims to answer one simple question:
"Which of these jobs should I actually apply to?"

## AI-Powered Recommendations
Each job receives a numerical score based on its overall fit with the candidate. The default values are:

| Score      | Recommendation                 | Meaning                                                                 |
| ---------- | ------------------------------ | ----------------------------------------------------------------------- |
| **75–100** | 🟢 Apply immediately           | Strong opportunity; prioritize the application                          |
|  **60–74** | 🟡 Apply (good stretch)        | Attractive opportunity with meaningful gaps or stretch requirements     |
|  **50–59** | 🟠 Only apply if you have time | Significant weaknesses or mismatches; lower priority                    |
|   **0–49** | 🔴 Do not apply                | Poor overall fit, major qualification gaps, or an important dealbreaker |

## Available Scrapers
- LinkedIn (guest/public website)

CareerLens is designed around a modular scraper architecture, so additional job sources can be added without rewriting the rest of the application.

## How It Works
At a high level, CareerLens uses a multi-stage pipeline:

Job Source -> Ingestion -> Filtering / Deduplication -> Staging
-> LLM Evaluation -> Scoring / Recommendation -> SQLite -> Interactive TUI

Job sources are handled by dedicated ingestion modules which convert externally collected postings into a common internal representation. From there, the rest of the application can process jobs without needing to know where they originally came from.

This separation was intentional: scraping, data processing, persistence, LLM evaluation, and presentation are treated as separate concerns.

### Design
CareerLens started as a personal automation project, but I wanted it to be more than a collection of scripts. The application therefore makes use of several software engineering concepts, including:

- Object-oriented design and inheritance for representing jobs and extending application components
- Multithreading for running long-running scraping and processing operations without blocking the user interface
- Callbacks for communicating progress and events between background processing and the UI
- Modular data pipelines for moving jobs through ingestion, filtering, evaluation, and persistence stages
- SQLite for lightweight local persistence
- Browser automation through Playwright for job-source ingestion
- Local LLM inference through Ollama
- Textual for the interactive terminal user interface (TUI)

One of the main design goals was to keep the application local-first. Job data, resumes, configuration, and LLM evaluation can all remain on the user's machine rather than being sent to a third-party job recommendation service.

### Database Design
CareerLens uses several SQLite tables to separate jobs at different stages of the processing pipeline:

- Companies: Maintains a record of companies encountered by CareerLens. This allows the application to track companies across job postings and apply company-level filtering.
- Ingest: The initial table for job sources where job identifiers and URLs must be collected separately from retrieving the full job posting.
- Staging: Contains jobs with the minimum information necessary for LLM evaluation. Keeping only the required data at this stage reduces unnecessary processing and context sent to the LLM.
- Jobs: Contains job postings that have passed the filtering and evaluation stages and that the candidate should consider applying to. This is the final destination for successfully processed jobs.
- Discarded: Contains jobs rejected during processing, whether through keyword filtering, company filtering, manual user dismissal, or LLM evaluation. Keeping discarded jobs allows CareerLens to avoid repeatedly processing the same postings.

## Current Limitations

CareerLens is currently a personal prototype rather than a production-ready application.

Some current limitations include:

- Linux is the only platform on which CareerLens has been tested. The project was specifically developed and tested on EndeavourOS using Linux kernel 7.1.9-arch1-2. Windows and macOS have not been tested.
- Ollama must already be installed and configured, including a compatible model.
- Playwright must already be installed and configured, including the required browser binaries.
- The default LLM model may require significant system resources. Performance will depend heavily on the model and available hardware.
- Job browsing currently loads a limited number of results rather than implementing full infinite scrolling (currently 100, sorted by most recent).
- Scraping currently runs to completion once started; proper cancellation and interruption handling are planned. The current workaround is to close the UI with Ctrl+Q and terminate the underlying process with Ctrl+C
- Some internal components are functional but would benefit from further refactoring.
- Website changes made by supported job sources may break scraper functionality.
- Company blacklist can only be set directly through the database.

These limitations are known and are part of the current prototype.

## Planned Features
Some ideas currently on the roadmap:

- Additional job-source scrapers
- Further refactoring and cleanup of the processing pipeline
- Improved UI/UX
- Better scraping interruption and cancellation support
- More flexible job-source configuration
- Additional filtering and recommendation options
- Access to the discarded table along with infinite scrolling
- Improved resource management for local LLMs
- The project is intentionally being released as a working prototype rather than waiting for every planned feature to be completed.

## Important: LinkedIn and Automated Access

Do not log into your personal LinkedIn account while using the current LinkedIn scraper. The scraper does not require or support authenticated LinkedIn access.

CareerLens currently accesses LinkedIn through its publicly accessible/guest-facing website. The scraper is not designed around authenticated access.

Automated access to third-party websites may be restricted by their terms of service, robots policies, rate limits, or other technical measures. Changes to those systems may also cause the scraper to stop working.

Use CareerLens responsibly and at your own discretion. **Do not provide CareerLens with your any credentials.**

## Motivation
Searching for a first job in tech can mean spending hours every day reading essentially the same job postings, figuring out whether you're qualified, and deciding whether each application is worth the effort.

I've been through that process myself. When you're sending out dozens of applications just to get a single interview, the process becomes exhausting surprisingly quickly. Even when you're doing everything you can to improve your resume, practice technical interviews, and apply strategically, the sheer volume of applications can make burnout feel like a very real risk.

CareerLens is my attempt to automate the most repetitive part of that process: finding and triaging opportunities.

The goal isn't to blindly apply to as many jobs as possible. It's to identify the opportunities that are actually worth my time, explain why they are a good fit, and help me spend my limited application time where it has the best chance of paying off.

What started as a personal tool for my own job search is also an experiment in seeing how far that idea can be taken.

## Disclaimer
CareerLens is a personal automation and recommendation project.

Job recommendations are generated algorithmically and should not be treated as a substitute for your own judgment. Job postings may contain incomplete, outdated, or misleading information, and an LLM's evaluation may be incorrect.

Automated access to third-party job websites may be subject to their terms of service and technical restrictions. Users are responsible for ensuring that their use of CareerLens complies with applicable terms and policies.

CareerLens is provided as-is for educational and personal use.
