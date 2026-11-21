# OmniDesk AI backend - development image.
# Python is pinned to 3.13 (Phase 0 decision) for reproducibility and to match
# the production target, decoupling from the host interpreter. A hardened
# multi-stage production image is introduced in Phase 10.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# --reload is for local development; the source tree is bind-mounted via compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
