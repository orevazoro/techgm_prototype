from typing import Type, TypeVar
from ollama import chat
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "qwen2.5:3b"

def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> T:
    """Calls local Ollama and enforces a Pydantic JSON schema."""
    response = chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        format=schema.model_json_schema(),
        options={"temperature": temperature},
    )
    return schema.model_validate_json(response.message.content)