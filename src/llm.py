import ollama

def generate_response(model: str, prompt: str) -> str:


    prompt = """
    - short_score: a simplified visual aid where there are 4 possibilities: "🟢 Apply immediately", 
    "🟡 Apply (good stretch)", "🟠 Only apply if you have time (bad stretch)", and "🔴 Do not apply", 
    with emojis and text included verbatim.
    - reasoning: short text that explains why you gave that particular job these scores: is the company attractive? 
    Does it match my career objectives? Does my resume match the job well? Do I have a decent shot at getting an interview?
    
    Return JSON with:
    {
        "score": integer 0-100,
        "short_score": string,
        "reasoning": string
    }
    Do not reply with any other text beyond what is enclosed within the JSON.
    """

    response = ollama.generate(
        model='deepseek-r1', # Or qwen3, gemma4, etc.
        prompt='What is the capital of France?',
        think=False  # <-- Disables the reasoning trace entirely
    )
    # response["response"]
    # TODO: assert all the funny stuff
    
    return ""