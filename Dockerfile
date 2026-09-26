FROM python:3.11-slim@sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e

WORKDIR /app

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY . .

# Säkerhetshärdning: Kör som icke-root användare
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
ENV PYTHONPATH=/app
ENV FIREBASE_PROJECT_ID=paygap-prod
ENV EMBEDDING_PROVIDER=mock

EXPOSE 8080

CMD ["python", "-m", "src.server"]

