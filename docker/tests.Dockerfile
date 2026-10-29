# Image that runs the test suite itself, browsers included.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /qa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["./scripts/run_suite.sh"]
