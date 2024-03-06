import os
import openai
import openai.error

def generate_from_openai_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    if "GPT4V_TOKEN" not in os.environ:
        raise ValueError(
            "OPENAI_API_KEY environment variable must be set when using OpenAI API."
        )
    openai.api_key = os.environ["GPT4V_TOKEN"]
    openai.organization = os.environ.get("OPENAI_ORGANIZATION", "")
    openai.api_base = "https://one-api.glm.ai/v1"

    response = openai.ChatCompletion.create(  # type: ignore
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stop=[stop_token] if stop_token else None,
    )
    answer: str = response["choices"][0]["message"]["content"]
    print(messages)
    print(answer)
    return answer
