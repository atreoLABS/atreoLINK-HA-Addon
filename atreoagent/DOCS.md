# atreoLINK

Runs [atreoLINK](https://atreolink.com) as a Home Assistant add-on: a WireGuard
tunnel terminator, ACL-enforcing reverse proxy, encrypted push relay, and opt-in
SMTP-to-push gateway for your self-hosted apps.

## Installation

1. Add this repository under **Settings → Add-ons → Add-on Store → ⋮ →
   Repositories**.
2. Install the **atreoLINK** add-on.
3. Adjust options if needed (defaults work for most setups), then **Start**.

## Pairing

On first start the agent needs to be paired with your atreoLINK account. The
add-on raises a **persistent notification** on your dashboard containing:

- a **pairing code** (to confirm you're approving *this* agent), and
- an **Approve pairing** link.

Open the link in your browser and approve. The notification clears itself once
pairing completes, and the agent reconnects automatically on every restart
afterwards. The approval link's `#fragment` stays in your browser and anchors
the owner identity key on this agent. It never reaches atreoLINK.

If you miss the notification, it is also printed in the add-on **Log** tab
(`Pairing code:` / `Approve at:`).

## Adding Home Assistant to atreoLINK

Once pairing completes, the add-on raises a **one-time notification** linking
straight to atreoLINK with the Home Assistant app already filled in: name,
address (`http://127.0.0.1:8123`), slug and icon. Review the values and press
**Create**.

The notification appears once and does not return. To add Home Assistant later,
go to your server in atreoLINK, choose **Manage**, and add an app manually with
those same values.

## Notifying family members from automations

The add-on can send **end-to-end-encrypted** push notifications to your
atreoLINK family members straight from Home Assistant automations. atreoLINK
relays only the ciphertext; only the recipient's devices can decrypt it.

### The bundled integration (recommended)

The add-on ships a Home Assistant integration and installs it for you on start.

1. Start the add-on, then **restart Home Assistant** (a notification reminds
   you). This is only needed the first time, and again after add-on updates.
2. The **atreoLINK** integration is discovered automatically. Accept it under
   **Settings → Devices & services**. If it isn't discovered, add it manually:
   **Add integration → atreoLINK** (host `127.0.0.1`, port `9876`, and the API
   key from your atreoLINK dashboard).

You then get one **`notify.*` entity per family member**, plus an
`atreolink.send_notification` action. No API key to copy in the common case.

```yaml
# Notify one member (entity per member, created automatically):
action: notify.send_message
target:
  entity_id: notify.atreolink_alice
data:
  title: "Washing machine"
  message: "Cycle finished at {{ now().strftime('%H:%M') }}"
```

```yaml
# Notify several members at once, with a severity and optional HTML body:
action: atreolink.send_notification
data:
  target:
    - alice@example.com
    - bob@example.com
  title: "Backup failed"
  message: "The nightly backup did not complete."
  severity: error
```

Members appear and disappear as you add or remove them in atreoLINK (refreshed
about once a minute).

### Notification fields

| Field | Notes |
|---|---|
| `userId` **or** `userEmail` | Exactly one; identifies the recipient member |
| `title` | Required; shown on the lock screen |
| `body` | Lock-screen excerpt |
| `html` / `plaintext` | Optional full body shown when the notification is opened |
| `severity` | `info` (default), `warning`, or `error` |

### Rotating the key

You can rotate the notify API key from the atreoLINK app. After rotating,
restart the add-on: the new key is re-published to the integration
automatically.

## Requirements

- **Host network + NET_ADMIN + /dev/net/tun.** The agent terminates WireGuard,
  installs an iptables firewall confining peers to the proxy ports, and discovers
  LAN endpoints, all of which need the host network namespace and `NET_ADMIN`.
- **WireGuard kernel module** on the host (built into Home Assistant OS).
- **UDP 51820 reachable** from the internet, via UPnP/NAT-PMP (on by default) or
  a manual router port-forward. Set a manual endpoint below if UPnP is disabled
  on your router.

## Options

| Option | Default | Notes |
|---|---|---|
| `log_level` | `info` | `debug`, `info`, `warn`, `error` |
| `wireguard_listen_port` | `51820` | UDP port WireGuard listens on |
| `wireguard_firewall_enabled` | `true` | Confine peers to the proxy ports. **Leave on.** |
| `wireguard_upnp_enabled` | `true` | Auto-map the WG port via UPnP/NAT-PMP |
| `endpoint_ip` | _(unset)_ | Manual public IP (when UPnP can't be used) |
| `endpoint_port` | _(unset)_ | Manual public UDP port |
| `proxy_enabled` | `true` | Built-in reverse proxy; disable to use your own |
| `proxy_http_port` | `80` | |
| `proxy_https_port` | `443` | |
| `proxy_auth_port` | `9091` | Forward-auth endpoint for external proxies |
| `proxy_trusted_networks` | _(empty)_ | CIDRs allowed to bypass auth (LAN). Opt-in. |
| `proxy_trusted_proxies` | _(empty)_ | CIDRs whose `X-Forwarded-*` headers are trusted |
| `ha_trust_proxy` | `true` | Auto-configure HA to trust the built-in reverse proxy (adds an `http:` block to `configuration.yaml`). See *Reverse-proxy trust* below. |
| `certs_email` | _(unset)_ | Let's Encrypt contact address |
| `notify_port` | `9876` | Local notification API (see *Notifying family members* above) |
| `smtp_enabled` | `false` | SMTP-to-push gateway (LAN-only) |
| `smtp_listen` | `0.0.0.0:2525` | Keep this bound to a LAN address |
| `smtp_max_message_bytes` | `1048576` | |
| `smtp_rate_per_minute` | `5` | Per source IP |
| `smtp_tls_enabled` | `false` | Opportunistic STARTTLS (self-signed) |

## Reverse-proxy trust

To reach **Home Assistant itself** through the atreoLINK tunnel, HA must trust
the add-on's built-in reverse proxy. With `ha_trust_proxy` on (the default), the
add-on does this for you: on start it appends a marked block to
`configuration.yaml` and asks you to **restart Home Assistant** to apply it:

```yaml
# >>> atreoLINK managed: reverse-proxy trust (do not edit) >>>
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
# <<< atreoLINK managed: reverse-proxy trust <<<
```

Trusting loopback is safe: the add-on shares the host network, so HA sees the
proxied requests from `127.0.0.1`, which is not reachable from outside the host.
A one-time backup is written to `configuration.yaml.atreolink.bak` before the
first edit.

If you **already have your own top-level `http:` block**, the add-on leaves it
untouched and instead posts a notification telling you to add `127.0.0.1` and
`::1` to `http.trusted_proxies` and set `use_x_forwarded_for: true` yourself.
Turn `ha_trust_proxy` off to remove the managed block (and stop the reminder).

## Data

All state (pairing identity, WireGuard + identity keys, ACL, issued
certificates, and the notification API key at `/data/notify_api_key`) is stored
on the add-on's persistent `/data` volume and is included in Home Assistant
backups. **Keep these backups.** The agent's identity key is irreplaceable
within a pairing lifecycle; losing it forces every paired client to re-pair.
