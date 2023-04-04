FROM mcr.microsoft.com/devcontainers/python:0-3.11

RUN apt-get update \
    && apt-get install -y \
        protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*
