# Security Policy

## Reporting a vulnerability

Please **do not** open public GitHub issues for security vulnerabilities.

Report security issues privately by either:

- Emailing **security@atreolabs.com**, or
- Using GitHub's [private vulnerability advisory](https://github.com/atreoLABS/atreoLINK-HA-Addon/security/advisories/new) feature.

For sensitive disclosures, prefer GitHub's private advisory — it offers built-in encryption and integrates with CVE issuance.

Include as much detail as you can: affected version / commit, reproduction steps, expected vs. actual behaviour, and any proof-of-concept. Reports will be promptly acknowledged and addressed.

## Supported versions

Only the latest release of the add-on is supported. There is no LTS — operators are expected to track the latest release.

The add-on image is layered on a pinned [atreoAGENT](https://github.com/atreoLABS/atreoAGENT) minor line (see `image/Dockerfile`), which must in turn run against the latest version of atreoLINK; older coordination-server versions are not supported.

## Threat model

This add-on packages [atreoAGENT](https://github.com/atreoLABS/atreoAGENT), which runs inside the server owner's trust boundary and explicitly distrusts the coordination server it talks to. Some non-obvious things to keep in mind when reporting:

- The coordination server is treated as a relay only. It cannot mint credentials, sign envelopes, or substitute keys. Findings that assume coordination-server compromise are still valuable; please describe the attacker capability.
- Per-app ACL enforcement happens **on the agent**, not on the coordination server. The agent pins owner identity at pairing time and verifies every state-changing message against the pinned key.
- The 25-second WebSocket keepalive is a known correctness invariant, not a tuning knob — please don't report it as a finding without context.
- The add-on runs **privileged** (`NET_ADMIN`, host network, `/dev/net/tun`) and mounts the Home Assistant config directory read-write to append a managed reverse-proxy-trust block to `configuration.yaml` — that added surface is in scope for this repo.

See atreoAGENT's [SECURITY.md](https://github.com/atreoLABS/atreoAGENT/blob/main/SECURITY.md) for the full agent threat model.

## Scope

In scope:

- Code in this repository: the add-on entrypoint (`image/run.sh`), `atreoagent/config.yaml`, the bundled `custom_components/atreolink` integration, and the image build configuration (`image/Dockerfile`).

Out of scope (please report to the relevant project / vendor instead):

- Issues in [atreoAGENT](https://github.com/atreoLABS/atreoAGENT) itself (report there).
- Issues in the closed-source coordination server (atreoLINK).
- Issues in Home Assistant Core or the Supervisor (report upstream).
- Issues in other upstream dependencies (file with the upstream project).
- Findings that require root access on the host the add-on runs on.
- Self-XSS / social engineering attacks against the operator.
