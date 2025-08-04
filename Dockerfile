FROM python:3.12-alpine

# Install UV package manager
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY examples/ ./examples/

# Install dependencies and the package
RUN uv sync

# Expose the discovery port
EXPOSE 8889

# Default command runs the discovery example
CMD ["uv", "run", "python", "examples/docker_discovery.py"]
