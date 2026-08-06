FROM python:3.13-slim

ARG APPNAME=weather

ENV PATH="/home/${APPNAME}/.local/bin:${PATH}" \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    useradd -m -s /bin/bash ${APPNAME} && \
    rm -rf /var/lib/apt/lists/*

USER ${APPNAME}

WORKDIR /home/${APPNAME}

RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

COPY --chown=${APPNAME}:${APPNAME} pyproject.toml poetry.lock ./

RUN poetry install \
    --no-root \
    --no-ansi \
    --without dev

COPY --chown=${APPNAME}:${APPNAME} . .

CMD ["poetry", "run", "uvicorn", "weather.app:app", "--host", "0.0.0.0", "--port", "8000"]