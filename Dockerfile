FROM python:3.11-slim

WORKDIR /app

# Installera nödvändiga systembibliotek
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Säkerhetshärdning: Kör som icke-root användare
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
ENV PYTHONPATH=/app
ENV FIREBASE_PROJECT_ID=mcp-las-rules
ENV EMBEDDING_PROVIDER=mock

EXPOSE 8080

CMD ["python", "-m", "src.server"]

