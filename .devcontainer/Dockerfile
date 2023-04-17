FROM mcr.microsoft.com/devcontainers/python:0-3.11

ARG PROTOC_VERSION=22.3
RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-x86_64.zip \
    && unzip protoc-${PROTOC_VERSION}-linux-x86_64.zip -d /usr/local \
    && rm protoc-${PROTOC_VERSION}-linux-x86_64.zip \
    && chmod +x /usr/local/bin/protoc
