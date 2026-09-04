FROM python:3.14-slim
WORKDIR /app
COPY env_lint ./env_lint
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "-m", "env_lint"]
