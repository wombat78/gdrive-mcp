FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8080
# Config via env: SERVICE_ACCOUNT_JSON|SERVICE_ACCOUNT_PATH, ALLOWED_FOLDER_IDS, GDRIVE_MCP_PORT
CMD ["gdrive-mcp"]
