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

# Copy application code
COPY scalper/data_system/               ./scalper/data_system/
COPY scalper/exchange_connector/        ./scalper/exchange_connector/
COPY scalper/scripts/__init__.py        ./scalper/scripts/__init__.py
COPY scalper/scripts/start_scalping.py  ./scalper/scripts/start_scalping.py
COPY scalper/strategy_manager/          ./scalper/strategy_manager/
COPY scalper/trade_executor/            ./scalper/trade_executor/
COPY scalper/utils/                     ./scalper/utils/

# Copy entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]