#!/bin/bash

HEADSCALE_PATH=external/headscale
OUTPUT_PATH=headscale_api/schema

PROTO_PATH=${HEADSCALE_PATH}/proto/
protoc --proto_path=${PROTO_PATH} --proto_path=external/googleapis/ \
    --experimental_allow_proto3_optional \
    --python_betterproto_out=${OUTPUT_PATH} \
    --python_betterproto_opt=pydantic_dataclasses \
    $(find ${PROTO_PATH} -name "*.proto")

# TODO: Compare external config example.
CONFIG_PATH=${HEADSCALE_PATH}/../config-example.yaml
datamodel-codegen --input ${CONFIG_PATH} --input-file-type yaml \
    --allow-extra-fields --force-optional --target-python-version 3.7 \
    --output ${OUTPUT_PATH}/config.py
