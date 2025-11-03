# ---------- Base image ----------
FROM python:3.11

# ---------- Locale setup ----------
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=ru_RU.UTF-8 \
    LC_ALL=ru_RU.UTF-8

# ---------- Install Poetry ----------
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# ---------- Working directory ----------
WORKDIR /app

# ---------- Copy dependency files (cached layer) ----------
COPY pyproject.toml poetry.lock* ./

# ---------- Install dependencies ONLY (skip project) ----------
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

# ---------- Copy full source code ----------
COPY . .

# ---------- Add PYTHONPATH to recognize 'python' package from src/ ----------
ENV PYTHONPATH=/app/src

# ---------- Run the app directly (via module) ----------
CMD ["python", "-m", "python.main"]
