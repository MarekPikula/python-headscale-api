#!/bin/bash

HEADSCALE_PATH=external/headscale
OUTPUT_PATH=headscale_api/schema

PROTO_PATH=${HEADSCALE_PATH}/proto/
protoc --proto_path=${PROTO_PATH} --proto_path=external/googleapis/ \
    --python_betterproto_out=${OUTPUT_PATH} $(find ${PROTO_PATH} -name "*.proto")

CONFI_PATH=${HEADSCALE_PATH}/config-example.yaml
datamodel-codegen --input ${CONFI_PATH} --input-file-type yaml \
    --allow-extra-fields --force-optional --target-python-version 3.7 \
    --output ${OUTPUT_PATH}/config.py
