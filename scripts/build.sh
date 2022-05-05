#!/bin/bash

set -e

git submodule update --init

docker build -f scripts/Dockerfile.build -t aerospike-wheel-builder:latest .

docker run -it -v $(pwd):/code aerospike-wheel-builder:latest /code/scripts/manylinuxbuild.sh
