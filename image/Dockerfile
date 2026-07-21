# The atreoAGENT base image, pinned to a minor line: rebuilds pick up 1.2.x
# patch releases but never a new minor. Bump this to move minor/major, and bump
# `version:` in atreoagent/config.yaml so users receive it. Override for a
# one-off build with `--build-arg AGENT_IMAGE=...`.
ARG AGENT_IMAGE=ghcr.io/atreolabs/atreoagent:1.2
FROM ${AGENT_IMAGE}

# bash (string handling), jq (parse add-on options + manifests), curl (Supervisor API).
RUN apk add --no-cache bash jq curl

# Bundled Home Assistant integration; run.sh installs it into the HA config dir
# on first start and whenever its version changes.
COPY custom_components/atreolink /opt/atreolink_integration

COPY image/run.sh /usr/local/bin/addon-run.sh
RUN chmod +x /usr/local/bin/addon-run.sh

# Reset the agent image's ENTRYPOINT so our wrapper runs (it execs the agent).
ENTRYPOINT []
CMD ["/usr/local/bin/addon-run.sh"]
