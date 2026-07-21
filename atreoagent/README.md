# Home Assistant Add-on: atreoLINK

Self-hosted [atreoLINK](https://atreolink.com) — WireGuard tunnel, ACL reverse
proxy, encrypted push notifications, and an opt-in SMTP-to-push gateway.

The pairing code and approval link are surfaced as a Home Assistant persistent
notification on first start, so you never have to dig through logs to pair.

It also installs a Home Assistant integration that gives you a `notify.*` entity
per family member, so automations can push end-to-end-encrypted notifications
straight to your family's phones.

See [DOCS.md](DOCS.md) for installation, pairing, notifications, options, and
requirements.
