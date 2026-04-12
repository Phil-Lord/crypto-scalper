# Official slim Python image from Docker Hub
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-group dev --no-group docs

# Make venv python the default
ENV PATH="/app/.venv/bin:$PATH"

# Add scalper/ to Python path so top-level module imports (data_system, etc.) resolve
ENV PYTHONPATH="/app/scalper"

# Copy the application code and entrypoint script
COPY scalper/ ./scalper/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]