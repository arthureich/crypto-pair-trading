# Use a lightweight python base image
FROM python:3.12-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project specification files
COPY pyproject.toml uv.lock ./

# Install dependencies without installing the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Final runtime stage
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY . /app

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run paper engine by default
CMD ["python", "-m", "src.paper.paper_engine"]
