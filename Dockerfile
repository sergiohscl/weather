FROM python:3.13.7-alpine3.22

ARG APPNAME=weather

ENV PATH="/home/${APPNAME}/.local/bin:${PATH}" \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN apk add --no-cache curl && \
    adduser -s /bin/sh -D ${APPNAME}

USER ${APPNAME}

WORKDIR /home/${APPNAME}

RUN curl -sSL https://install.python-poetry.org | python3 - --version ${POETRY_VERSION}

COPY pyproject.toml poetry.lock ./

RUN poetry install \
        --no-root \
        --no-ansi \
        --without dev

COPY . .

CMD ["poetry", "run", "uvicorn", "weather.app:app", "--host", "0.0.0.0", "--port", "8000"]