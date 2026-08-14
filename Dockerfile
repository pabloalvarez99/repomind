FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system repomind && adduser --system --ingroup repomind repomind

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY fixtures ./fixtures
COPY data ./data
RUN python -m pip install --no-cache-dir .

USER repomind
EXPOSE 8020

CMD ["python", "-m", "uvicorn", "repomind.main:app", "--host", "0.0.0.0", "--port", "8020"]
