import uvicorn

from backend.command_app import command_app
from backend.config import load_settings


if __name__ == "__main__":
    settings = load_settings()
    uvicorn.run(command_app, host="0.0.0.0", port=settings.command_api_port)
