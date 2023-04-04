#!/bin/bash

PROTO_PATH=external/headscale/proto/
OUTPUT_PATH=headscale_api/schema

protoc --proto_path=${PROTO_PATH} --proto_path=external/googleapis/ \
    --python_betterproto_out=${OUTPUT_PATH} $(find ${PROTO_PATH} -name "*.proto")
