#!/bin/bash

set -e

# Compile wheels
for PYBIN in /opt/python/*/bin; do
    "${PYBIN}/pip" wheel ./ -w /code/work/tempwheels
done

# Bundle external shared libraries into the wheels
for whl in /code/work/tempwheels/*.whl; do
    auditwheel repair "$whl" --plat manylinux_2_24_x86_64 -w /code/work/wheels/
done

for PYBIN in /opt/python/*/bin/; do
    ${PYBIN}/pip install aerospike -f /code/work/wheels/ --no-index
    ${PYBIN}/python -c "import aerospike; print('Installed aerospike version{}'.format(aerospike.__version__))"
done
