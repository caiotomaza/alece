FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app/src/controller:/app
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app --home /home/app app
COPY src/requirements/ /app/src/requirements/
RUN python -m pip install --no-cache-dir "pip==26.2.1" \
    && python -m pip install --no-cache-dir --require-hashes -r src/requirements/production.lock
COPY . /app
RUN ALECE_SECRET_KEY="temporary-build-only-secret-do-not-use" ALECE_DB_PASSWORD="temporary-build" python manage.py collectstatic --noinput \
    && mkdir -p /app/media /app/src/logs /app/private/ai /home/app/backups \
    && chown -R app:app /app/media /app/src/logs /app/private/ai /home/app
RUN chmod 0700 /app/private/ai
USER app
EXPOSE 8000
# Envolve a inicialização somente se ALECE_LOG_VALIDACAO=true.
CMD ["python", "/app/docker/logged_start.py", "sh", "/app/docker/start.sh"]
