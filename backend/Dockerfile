# SORA Copilot backend — multi-stage, slim final image.
# Python is pinned to 3.12 (build spec §2). WeasyPrint needs system libraries at
# runtime, not only at build time, so they are installed in the final stage.

# ---------------------------------------------------------------- builder
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# pyproj and shapely ship manylinux wheels; build tools are here only as a fallback
# for any source-only transitive dependency.
RUN apt-get update && apt-get install --no-install-recommends -y \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Dependencies resolve from pyproject alone, so this layer caches across code changes.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py \
    && pip install --upgrade pip \
    && pip install .

COPY app ./app
COPY scripts ./scripts
RUN pip install --no-deps .

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# WeasyPrint runtime libraries (build spec §14) plus a font so PDF output is not blank.
RUN apt-get update && apt-get install --no-install-recommends -y \
      libcairo2 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libpangoft2-1.0-0 \
      libgdk-pixbuf-2.0-0 \
      libffi8 \
      shared-mime-info \
      fonts-dejavu-core \
      curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /srv
COPY app ./app
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 sora && chown -R sora:sora /srv
USER sora

EXPOSE 8000

# /healthz is dependency-free by design, so this stays green while Supabase is paused.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" > /dev/null || exit 1

# Render supplies $PORT; the default keeps local runs identical.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
