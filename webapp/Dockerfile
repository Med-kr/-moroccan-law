# moroccan-law web app — local / on-premise. Build from the repository root:
#   docker compose -f webapp/docker-compose.yml up --build
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MOROCCAN_LAW_DATA=/data MOROCCAN_LAW_REPO=/app
WORKDIR /app
COPY webapp/requirements.txt webapp/requirements.txt
RUN pip install --no-cache-dir -r webapp/requirements.txt
COPY tools tools
COPY mcp mcp
COPY skills skills
COPY webapp webapp
RUN useradd --create-home --uid 10001 mlaw && mkdir -p /data && chown mlaw /data
USER mlaw
EXPOSE 8000
CMD ["uvicorn", "webapp.app:app", "--host", "0.0.0.0", "--port", "8000"]
