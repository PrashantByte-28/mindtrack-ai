FROM python:3.14-slim

# Python configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Add uv virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy project files
COPY . .

# Install locked production dependencies
RUN uv sync --frozen --no-dev

# Keep the SQLite database on a volume so accounts survive container restarts.
# Without a volume the database is deleted together with the container.
RUN mkdir -p /data
ENV MINDTRACK_DB_PATH=/data/mindtrack.db
VOLUME ["/data"]

# Streamlit port
EXPOSE 8501

# Start Streamlit
CMD ["sh", "-c", "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]