# atreoLINK Home Assistant Add-on

A Home Assistant add-on that packages [atreoLINK](https://atreolink.com) (the
[atreoAGENT](https://github.com/atreoLABS/atreoAGENT) daemon) so it can be
installed, configured, and paired entirely from the Home Assistant UI.

[![Add repository to your Home Assistant instance.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FatreoLABS%2FatreoLINK-HA-Addon)

## Highlights

- **First-class config UI:** every agent option is exposed in the add-on
  Options tab; no hand-editing YAML.
- **One-click pairing:** the pairing code and approval link appear as a Home
  Assistant persistent notification on first start, and clear themselves once
  pairing succeeds.
- **Notify your family from automations:** a bundled integration is installed
  automatically, giving you a `notify.*` entity per family member for
  end-to-end-encrypted push notifications.
- **Persistent & backed up:** pairing identity, keys, ACL, and certificates
  live on the add-on's `/data` volume and are captured by Home Assistant backups.

## Install

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, and add this repo's
   URL.
2. Install **atreoLINK**, tweak options if desired, and **Start**.
3. Approve the pairing notification that appears on your dashboard.

Add-on documentation: [`atreoagent/DOCS.md`](atreoagent/DOCS.md).

## Contributing

Home Assistant pulls a prebuilt multi-arch image, so there is nothing to build to
use the add-on. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup,
how the image is assembled, and how releases are cut.

## License

Apache-2.0. See [LICENSE](LICENSE). The agent it packages,
[atreoAGENT](https://github.com/atreoLABS/atreoAGENT), is also Apache-2.0.
