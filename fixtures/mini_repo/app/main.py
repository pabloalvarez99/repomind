"""Application assembly for the fixture service."""

from app.service import GreetingService


def create_app() -> dict[str, object]:
    """Create the fixture application and wire its greeting service."""
    service = GreetingService(prefix="Hello")
    return {"name": "mini-service", "greet": service.greet}


async def health() -> dict[str, str]:
    """Return the fixture process liveness payload."""
    return {"status": "ok"}
