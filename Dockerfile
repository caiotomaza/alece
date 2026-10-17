FROM python:3.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app --home /home/app app
COPY requirements/ /app/requirements/
RUN python -m pip install --no-cache-dir -r requirements/production.txt
COPY . /app
RUN ALECE_SECRET_KEY="build-only-key-not-used-at-runtime-$(date +%s)" \
    ALECE_DB_PASSWORD="build-only-unused" python manage.py collectstatic --noinput \
    && mkdir -p /app/media && chown -R app:app /app/staticfiles /app/media /home/app
USER app
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]
