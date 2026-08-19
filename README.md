# CareerLens
A privacy-focused, local-first, AI-powered job search and recommendation engine that finds job postings, filters out irrelevant opportunities, evaluates them against your career goals and resume, and tells you which ones are actually worth applying to.

The goal is simple: spend less time looking for jobs and more time applying to the right ones.

## What it does
CareerLens automates much of the tedious work involved in a modern job search:
- Scrapes job postings from supported job boards
- Filters jobs using configurable keywords and company blacklists
- Evaluates jobs with an LLM against your resume, skills, career goals, and preferences
- Scores opportunities from 0–100
- Provides a short recommendation and reasoning explaining why a job is or isn't a good fit
- Prioritizes applications so you can focus your time where it matters

Instead of giving you hundreds of job postings to sift through, CareerLens aims to answer one simple question:
"Which of these jobs should I actually apply to?"

## AI-Powered Recommendations
Each job receives a numerical score based on its overall fit with the candidate.

| Score      | Recommendation                 | Meaning                                                                 |
| ---------- | ------------------------------ | ----------------------------------------------------------------------- |
| **75–100** | 🟢 Apply immediately           | Strong opportunity; prioritize the application                          |
|  **60–74** | 🟡 Apply (good stretch)        | Attractive opportunity with meaningful gaps or stretch requirements     |
|  **50–59** | 🟠 Only apply if you have time | Significant weaknesses or mismatches; lower priority                    |
|   **0–49** | 🔴 Do not apply                | Poor overall fit, major qualification gaps, or an important dealbreaker |

## Motivation
Searching for a first job in tech can mean spending hours every day reading essentially the same job postings, figuring out whether you're qualified, and deciding whether each application is worth the effort.

I've been through that process myself. When you're sending out dozens of applications just to get a single interview, the process becomes exhausting surprisingly quickly. Even when you're doing everything you can to improve your resume, practice technical interviews, and apply strategically, the sheer volume of applications can make burnout feel like a very real risk.

CareerLens is my attempt to automate the most repetitive part of that process: finding and triaging opportunities.

The goal isn't to blindly apply to as many jobs as possible. It's to identify the opportunities that are actually worth my time, explain why they are a good fit, and help me spend my limited application time where it has the best chance of paying off.

What started as a personal tool for my own job search is also an experiment in seeing how far that idea can be taken.

## Disclaimer
CareerLens is a personal automation and recommendation project. Automated access to job boards may be subject to their terms of service and technical restrictions. Use responsibly.