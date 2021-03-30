#!/bin/sh

set -eo pipefail

cp /flyteorg/share/flyte_generated.yaml /opt/flyteorg/share/deployment
kustomize build /opt/flyteorg/share/deployment | tee /flyteorg/share/flyte_generated.yaml

exec "$@"
