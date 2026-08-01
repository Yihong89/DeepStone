FROM python:3.11-slim

WORKDIR /srv

# git is needed by pip to install fireplace from its git URL.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt

COPY backend /srv/backend
WORKDIR /srv/backend

# Fetch the real CardDefs.xml (Fireplace ships an unresolved git-LFS stub) and
# generate the deck-builder card universe from the engine's own data.
RUN python scripts/ensure_fireplace_data.py && python scripts/build_cards.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
