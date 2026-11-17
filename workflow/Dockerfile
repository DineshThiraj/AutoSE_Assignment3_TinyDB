FROM python:3.12-slim
# Trusted environment build occurs before generated source is mounted.
# Pin the resulting image ID in each run's execution evidence.
RUN python -m pip install --no-cache-dir pytest==9.2.0 PyYAML==6.0.3
ENV PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
WORKDIR /work
