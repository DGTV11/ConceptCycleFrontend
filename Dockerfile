FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ADD . /app

WORKDIR /app

RUN uv sync --locked --compile-bytecode

ENV GRADIO_SERVER_NAME="0.0.0.0"

ENTRYPOINT ["uv", "run", "main.py"]
