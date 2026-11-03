"""Safe chatbot errors that never expose provider details."""

from app.core.errors import ApplicationError


class ChatbotUnavailableError(ApplicationError):
    def __init__(
        self,
        detail: str = "Chatbot is temporarily unavailable. Please try again later.",
        code: str = "chatbot_unavailable",
    ) -> None:
        super().__init__(503, code, detail)


class ChatbotInvalidResponseError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            502,
            "chatbot_invalid_response",
            "Chatbot returned an invalid response. Please try again.",
        )
