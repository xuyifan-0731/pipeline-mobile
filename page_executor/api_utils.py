SCREENSHOT_CLF_PROMPT = """You are a professional visual language question answer system that can answer user's question according to the screenshot provided. You will strictly follow user's output format requirement, and do not generate any additional contents that are not asked by the user. Your answer is honestly based on the visual information from the screenshot.
"""


def screenshot_contains(engine, keywords, screenshot):
    return engine.single_turn_generation(
        system_prompt=SCREENSHOT_CLF_PROMPT,
        prompt=f"Does the screenshot contains '{keywords}'? Answer 'Yes' or 'No' only.",
        image_path=screenshot
    ) == 'Yes'


def screenshot_satisfies(engine, condition, screenshot):
    response = engine.single_turn_generation(
        system_prompt=SCREENSHOT_CLF_PROMPT,
        prompt=f"{condition}? Answer 'Yes' or 'No' only.",
        image_path=screenshot
    )
    print(f"Call screenshot_satisfies(condition='{condition}'): {response}")
    return response == 'Yes'
