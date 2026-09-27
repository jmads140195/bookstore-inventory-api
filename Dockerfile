FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup --system app && adduser --system --ingroup app app
COPY --chown=app:app . .
RUN chmod +x docker/entrypoint.sh \
    && DJANGO_ENV=development DJANGO_DEBUG=false python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:'+os.getenv('PORT','8000')+'/ready', headers={'X-Forwarded-Proto':'https'}); urllib.request.urlopen(r,timeout=3)"
CMD ["/app/docker/entrypoint.sh"]
