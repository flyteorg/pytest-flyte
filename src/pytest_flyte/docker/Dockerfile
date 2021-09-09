FROM ghcr.io/flyteorg/flyte-sandbox:dind

# Enable docker buildkit
ENV DOCKER_BUILDKIT=1

ENTRYPOINT ["tini", "flyte-entrypoint.sh"]
