import json
from dataclasses import dataclass

import ollama
from typing_extensions import Any

from scrapers.scraper_utilities import JobData, JobListing, JobStatus


@dataclass
class LLMResponse:
    score: int
    short_score: str
    reasoning: str

def generate_response(config: dict[str, Any], prompt: str) -> str:
    try:
        response = ollama.generate(
            model = config["llm"]["model"], 
            prompt = prompt, 
            think = False,
            options={"num_ctx": 16384}
        )
        return response["response"]
    except:
            raise RuntimeError("LLM generation failed")


def parse_llm_response(config: dict[str, Any], response: str) -> LLMResponse:
    required_fields = {"score", "short_score", "reasoning"}
    try:
        data = json.loads(response)
    except:
        raise Exception("LLM returned invalid JSON")
    if not isinstance(data, dict):
        raise Exception("LLM response must be a JSON object")
    if set(data.keys()) != required_fields:
        raise Exception(f"LLM response must contain exactly: {required_fields}")

    score = data["score"]
    if type(score) is not int:
        try:
            score = int(score)
        except:
            raise Exception("LLM score must be an integer")
    if not 0 <= score <= 100:
        raise Exception("LLM score must be between 0 and 100")

    # TODO: make sure it's exactly 1 of 4 values, maybe with enum
    short_score = data["short_score"]
    if not isinstance(short_score, str):
        raise Exception("LLM short_score must be a string")

    reasoning = data["reasoning"]
    if not isinstance(reasoning, str):
        raise Exception("LLM reasoning must be a string")

    return LLMResponse(score, short_score, reasoning)


def use_llm(config: dict[str, Any], job: JobData) -> JobListing:
    llm_config = config["llm"]
    prompt = """You are evaluating a job posting for a specific job candidate.
    
    Your task is to determine how strongly this job matches the candidate's 
    career goals, preferences, experience, and qualifications.
    
    The score is a JOB FIT SCORE, not a probability of getting hired. 
    A high score means the candidate should strongly consider applying. 
    A low score means the candidate should probably skip the job.

    ## CANDIDATE PROFILE
    
    The candidate's resume, when provided, represents their actual experience, 
    education, skills, and qualifications.
    
    The candidate may also provide optional preferences, goals, and constraints.

    IMPORTANT:
    - Assume that the candidate is legally authorized to work in the country where the job is located and does not require sponsorship.
    - Only consider preferences and goals that are explicitly provided.
    - If a preference category is not provided, treat it as NEUTRAL.
    - Do not penalize or reward the candidate based on a preference that was not specified.
    - Do not invent preferences, career goals, or dealbreakers that were not provided.
    - Dealbreakers that ARE explicitly provided should be treated as significant negative factors.
    - The resume should be used as evidence when assessing qualifications and technical fit.
    - Do not assume that the candidate has experience or qualifications that are not supported by the resume.
    
    """
    
    if llm_config["career_goals"]:
        prompt += f"Career goals:\n{llm_config['career_goals']}\n\n"
    if llm_config["preferred_roles"]:
        prompt += ("Preferred roles:\n- " + "\n- ".join(llm_config["preferred_roles"]) + "\n\n")
    if llm_config["preferred_technologies"]:
        prompt += ("Preferred technologies:\n- " + "\n- ".join(llm_config["preferred_technologies"]) + "\n\n")
    if llm_config["excluded_roles"]:
        prompt += ("Roles the candidate does not want:\n- " + "\n- ".join(llm_config["excluded_roles"]) + "\n\n")
    if llm_config["excluded_roles"]:
        prompt += ("Roles the candidate does not want:\n- " + "\n- ".join(llm_config["excluded_roles"]) + "\n\n")
    if llm_config["preferred_industries"]:
        prompt += ("Preferred industries:\n- " + "\n- ".join(llm_config["preferred_industries"]) + "\n\n")
    if llm_config["priorities"]:
        prompt += ("Priorities:\n- " + "\n- ".join(llm_config["priorities"]) + "\n\n")
    if llm_config["dealbreakers"]:
        prompt += ("Dealbreakers:\n- " + "\n- ".join(llm_config["dealbreakers"]) + "\n\n")
    if llm_config["resume"]:
        prompt += f"### RESUME\n{llm_config['resume']}\n\n"

    prompt += f"""
    ## JOB POSTING

    Title: {job.title}
    Company: {job.company}
    Location: {job.location}
    Description: {job.description}
    \n
    """
    
    prompt += """
    ## EVALUATION

    Evaluate the job using the following factors, but only apply factors for 
    which relevant candidate information is available.
    
    1. Career alignment
    Does this role help the candidate move toward their stated career goals?
    Consider:
    - The actual responsibilities of the position.
    - The type of work the candidate wants to perform.
    - Whether the position represents a useful career progression.
    If career goals were not provided, do not infer them.
    
    2. Role alignment
    How closely does the position match the candidate's preferred roles?
    If preferred roles were provided:
    - Reward close matches.
    - Penalize roles that are explicitly excluded.
    - Consider the actual responsibilities rather than relying solely on the job title.
    If no preferred or excluded roles were provided, treat this factor as neutral.
    
    3. Technical alignment
    How well do the technologies, programming languages, systems, infrastructure, and technical responsibilities match the candidate's skills and preferences?
    Consider:
    - Existing skills demonstrated by the resume.
    - Technologies the candidate explicitly prefers.
    - The proportion of the job that involves the candidate's desired technical work.
    Do not penalize the candidate merely because they do not know every technology listed in the posting. Distinguish between essential requirements and technologies that could reasonably be learned on the job.
    
    4. Qualifications
    How well does the candidate's resume match the actual requirements of the position?
    Distinguish between:
    - Hard requirements.
    - Strong preferences.
    - Nice-to-have qualifications.
    Do not assume that every requirement listed in a job posting is equally important.
    Do not reject a candidate solely because they lack a nice-to-have qualification.
    
    5. Industry alignment
    Does the company and industry match the candidate's stated preferences?
    If preferred industries were provided, reward relevant matches and penalize significant mismatches.
    If no industry preferences were provided, treat this factor as neutral.
    
    6. Priorities
    Consider the candidate's explicitly stated priorities.
    A job that strongly satisfies an important priority should receive a meaningful positive adjustment.
    A job that conflicts with an important priority should receive a meaningful negative adjustment.
    If no priorities were provided, treat this factor as neutral.
    
    7. Dealbreakers
    Explicit dealbreakers should be taken seriously.
    If the job clearly violates an explicitly stated dealbreaker, this should have a major negative effect on the score and may justify recommending that the candidate not apply.
    Do not invent dealbreakers that the candidate did not provide.
    
    8. Overall attractiveness
    Consider whether this is a job the candidate would actually want, rather than merely whether they could technically perform it.
    A technically strong match can still be a poor recommendation if it conflicts with the candidate's explicitly stated goals, preferences, priorities, or dealbreakers.
    Conversely, a job does not need to match every preference perfectly to be a strong opportunity.

    ## SCORE
    Assign an integer score from 0 to 100.
    
    Use the following general interpretation:
    90-100: Exceptional opportunity. Very strong overall alignment with the candidate's goals, preferences, and qualifications.
    75-89: Strong opportunity. Clearly worth applying to, although there may be some gaps or compromises.
    60-74: Reasonable opportunity. There are meaningful weaknesses or stretches, but the job may still be worth applying to.
    40-59: Weak opportunity. There is a significant mismatch or substantial stretch.
    0-39: Poor opportunity. There is a major mismatch, significant lack of qualifications, or an explicit dealbreaker.
    
    The score represents the overall attractiveness and fit of the job to this candidate. It is NOT:
    - a probability of getting an interview,
    - a probability of getting hired,
    - an estimate of the number of competing applicants,
    - or a measure of how prestigious the company is.
    Do not speculate about the number of applicants or the candidate's probability of receiving an interview.

    ## SHORT SCORE
    
    Choose exactly ONE of the following values, including the emoji and text verbatim:
    "🟢 Apply immediately"
    "🟡 Apply (good stretch)"
    "🟠 Only apply if you have time (bad stretch)"
    "🔴 Do not apply"
    
    Use the recommendation as follows:
    🟢 Apply immediately:
    The job is a strong opportunity and should be prioritized. Numerical scores from 75–100.
    🟡 Apply (good stretch):
    The job is attractive but contains meaningful gaps or stretch requirements. The candidate should still consider applying. Numerical scores from 60-74.
    🟠 Only apply if you have time (bad stretch):
    The job has substantial weaknesses or mismatches. Applying is reasonable only if the candidate has sufficient time and application capacity. Numerical scores from 50-59.
    🔴 Do not apply:
    The job is a poor overall match, conflicts with an important preference or dealbreaker, or has sufficiently significant qualification gaps that applying is unlikely to be worthwhile. Numerical score below 50.
    
    The short score must be consistent with the overall score and reasoning.
    
    ## REASONING
    Provide a concise explanation of the recommendation.
    Focus on the factors that most influenced the evaluation.
    Where relevant, mention:
    - Career alignment.
    - Role alignment.
    - Technical alignment.
    - Relevant qualifications and experience.
    - Important gaps.
    - Industry alignment.
    - Priorities.
    - Dealbreakers.
    Do not simply repeat the job description.
    Do not speculate about applicant counts or hiring probabilities.

    ## OUTPUT FORMAT
    Return ONLY a valid JSON object with exactly these three fields:
    
    {
    "score": integer,
    "short_score": string,
    "reasoning": string
    }
    
    Requirements:
    
    "score" must be an integer between 0 and 100 inclusive.
    "short_score" must be exactly one of the four values specified above.
    "reasoning" must be a concise string.
    The score, short_score, and reasoning must be consistent with one another.
    Do not include Markdown.
    Do not include code fences.
    Do not include explanations or any text outside the JSON object.
    """

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            response_candidate = generate_response(config, prompt)
            valid_response = parse_llm_response(config, response_candidate)
            break
        except:
            print(f"LLM attempt {attempt + 1}/{MAX_RETRIES} failed")
    else:
        raise Exception("LLM failed after 3 attempts")

    # If successful: write to db
    return JobListing(
        job.title,
        job.company,
        job.location,
        job.description,
        job.source,
        job.job_id,
        job.url,
        JobStatus.PENDING_MANUAL_REVIEW,
        None,
        valid_response.score,
        valid_response.short_score,
        valid_response.reasoning
    )