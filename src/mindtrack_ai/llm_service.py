
import os
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-20b"
MAX_CONTEXT_MESSAGES = 12
MAX_MESSAGE_CHARS = 4000
MAX_OUTPUT_TOKENS = 700
REQUEST_TIMEOUT_SECONDS = 30

ALLOWED_MOODS = {
    "Happy",
    "Calm",
    "Neutral",
    "Sad",
    "Stressed",
    "Anxious",
    "Overwhelmed",
}


SYSTEM_PROMPT = """
You are MindTrack AI, a supportive wellness and mood-reflection companion.

Your responsibilities:
- Respond with empathy, warmth, respect, and clear language.
- Help the user reflect on emotions, stress, sleep, routines, and coping
  strategies without judging them.
- Offer small, practical, optional steps rather than overwhelming advice.
- Ask one thoughtful follow-up question when it would be helpful.
- Respect the user's autonomy. Do not pressure them to share details.
- Never diagnose a mental health condition or claim to be a therapist.
- Do not claim that a suggestion will cure a condition.
- Encourage professional support when a concern is persistent, severe,
  or affecting daily life.
- Do not claim to have accessed private records unless the user has
  actually shared the relevant information in this conversation.
- If the user describes immediate danger, encourage contacting local
  emergency services and a trusted person.

Mood-aware response guidelines:
- Use the user's explicitly selected current mood as optional context.
- Adapt your tone and suggestions to that mood when relevant.
- For stress, anxiety, or overwhelm, consider one small grounding or
  practical coping step instead of a long list.
- For sadness, acknowledge the feeling without minimizing it or forcing
  positivity.
- For calm or happy moods, support reflection and healthy routines when
  relevant.
- Never assume you know the cause, severity, or full meaning of a mood.
- Do not treat a mood selection as a diagnosis or a complete picture.
- If the user changes or corrects their mood, respect their latest message.
- If no mood is supplied, respond normally without guessing the mood.
- Do not repeatedly mention the selected mood if it adds no value.

This is a wellness application, not a diagnostic or emergency service.
Keep responses concise, supportive, and easy to understand.
""".strip()


@lru_cache(maxsize=1)
def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to your local .env file."
        )

    return Groq(
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=1,
    )


def _prepare_messages(
    conversation_messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Validate and limit chat history before sending it to the model."""
    cleaned_messages = []

    for message in conversation_messages[-MAX_CONTEXT_MESSAGES:]:
        role = message.get("role")
        content = message.get("content")

        if role not in {"user", "assistant"}:
            continue

        if not isinstance(content, str) or not content.strip():
            continue

        cleaned_messages.append(
            {
                "role": role,
                "content": content.strip()[-MAX_MESSAGE_CHARS:],
            }
        )

    if not cleaned_messages or cleaned_messages[-1]["role"] != "user":
        raise ValueError(
            "The conversation must end with a user message."
        )

    return cleaned_messages



def generate_response(
    conversation_messages: list[dict[str, str]],
    mood_context: str | None = None,
) -> str:
    """
    Generate a wellness response using saved chat history
    and optional user-selected mood context.
    """
    prepared_messages = _prepare_messages(conversation_messages)

    system_prompt = SYSTEM_PROMPT

    if mood_context is not None:
        mood_context = mood_context.strip()

        if mood_context not in ALLOWED_MOODS:
            raise ValueError("The selected mood is not supported.")

        system_prompt += (
            "\n\nThe user has voluntarily selected this current mood: "
            f"{mood_context}.\n"
            "Adapt your tone and suggestions when relevant. "
            "Do not assume the cause or severity of this mood. "
            "For stress or overwhelm, offer one manageable step. "
            "For sadness, acknowledge feelings without minimizing them. "
            "Do not diagnose or force positivity. "
            "Respect any mood correction the user shares."
        )

    model_name = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip()

    if not model_name:
        model_name = DEFAULT_MODEL

    messages = [
        {"role": "system", "content": system_prompt},
        *prepared_messages,
    ]

    response = _get_client().chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.4,
        max_tokens=MAX_OUTPUT_TOKENS,
    )

    answer = response.choices[0].message.content

    if not answer or not answer.strip():
        raise RuntimeError("The AI service returned an empty response.")

    return answer.strip()