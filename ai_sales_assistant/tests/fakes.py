from app.prompts.base import Prompt
from app.services.ai.base import AIResult
from app.services.email import EmailMessage


class FakeAIProvider:
    """In-memory AIProvider that records prompts and returns a canned result or raises."""

    name = "fake"

    def __init__(self, content: str = "Generated content", error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.prompts: list[Prompt] = []
        # Optional scripted answers, one per call (then `content` again).
        self.responses: list[str] = []

    def generate(self, prompt: Prompt) -> AIResult:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return AIResult(
            content=self.responses.pop(0) if self.responses else self.content,
            provider=self.name,
            model="fake-model",
            prompt_tokens=100,
            completion_tokens=50,
        )


class FakeEmailSender:
    """In-memory EmailSender that records every message instead of sending it."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.messages.append(message)
