"""Business service for the fixture application."""


class GreetingService:
    """Render deterministic greetings with a configured prefix."""

    def __init__(self, prefix: str) -> None:
        """Store the greeting prefix."""
        self.prefix = prefix

    def greet(self, name: str) -> str:
        """Return a greeting for ``name``."""
        return f"{self.prefix}, {name}!"
