import os
import openai
import openai.error

def generate_from_openai_completion(
    prompt: str,
) -> str:
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError(
            "OPENAI_API_KEY environment variable must be set when using OpenAI API."
        )
    openai.api_key = os.environ["OPENAI_API_KEY"]
    openai.organization = os.environ.get("OPENAI_ORGANIZATION", "")
    openai.api_base = "https://one-api.glm.ai/v1"
    response = openai.Completion.create(  # type: ignore
        prompt=prompt,
    )
    answer: str = response["choices"][0]["text"]
    return answer