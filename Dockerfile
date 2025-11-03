# Use official Python 3.11 image as base
FROM python:3.11

# Set up Russian UTF-8 locale (non-interactive)
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    rm -rf /var/lib/apt/lists/*

# Set locale environment variables
ENV LANG=ru_RU.UTF-8
ENV LC_ALL=ru_RU.UTF-8

# Install Poetry (global install via symlink for easier use)
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set working directory
WORKDIR /app

# Copy only dependency files first, enables Docker layer caching
COPY pyproject.toml poetry.lock* ./

# Configure Poetry and install dependencies (without creating virtualenv)
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# Now copy the full application code
# This layer will be invalidated only when code changes, not dependencies
COPY . .

# Run the application using Poetry
CMD ["poetry", "run", "csohelper"]