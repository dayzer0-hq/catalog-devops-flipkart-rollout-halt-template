FROM python:3.12-slim

COPY app/ /srv/app/
WORKDIR /srv

# The GOOD image. The broken tag is this same image built with BREAK_READINESS=1 baked in —
# see Dockerfile.broken, which is how one codebase produces both tags.
ENV WARMUP_SECONDS=3
EXPOSE 8080
CMD ["python3", "app/server.py"]
