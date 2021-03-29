FROM ghcr.io/flyteorg/flyte-sandbox:dind

# Install kustomize
ARG KUSTOMIZE_VERSION="v4.0.5"
RUN wget -q -O /tmp/kustomize.tar.gz https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_amd64.tar.gz \
    && tar -xf /tmp/kustomize.tar.gz -C /flyteorg/bin \
    && chmod +x /flyteorg/bin/kustomize \
    && rm /tmp/kustomize.tar.gz

COPY flyte-entrypoint-override.sh /flyteorg/bin/

# Enable docker buildkit
ENV DOCKER_BUILDKIT=1

ENTRYPOINT ["tini", "flyte-entrypoint-override.sh", "flyte-entrypoint.sh"]
