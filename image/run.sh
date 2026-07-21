#!/usr/bin/env bash
# Home Assistant add-on entrypoint: render the agent config from the add-on
# options, supervise the agent, and surface the pairing URL as a notification.
set -euo pipefail

DATA_DIR=/data
CONFIG_FILE="${DATA_DIR}/config.yaml"
OPTIONS="${DATA_DIR}/options.json"
NOTIFY_ID=atreoagent_pairing
INTEGRATION_NOTIFY_ID=atreoagent_integration
PROXY_TRUST_NOTIFY_ID=atreoagent_proxy_trust
KEY_FILE="${DATA_DIR}/notify_api_key"
PAIRING_FILE="${DATA_DIR}/pairing.json"
APP_PROMPT_SENTINEL="${DATA_DIR}/.ha_app_prompt_done"
ADD_APP_NOTIFY_ID=atreoagent_add_app
ATREOLINK_APP_URL="https://app.atreolink.com"
ADD_APP_PRESET=home-assistant
# Set by ha_service on every call; read by callers that need to know whether
# delivery actually succeeded (as opposed to ha_service's own return value,
# which is always 0 — see ha_service for why).
HA_SERVICE_OK=true
# Bundled by the Dockerfile; installed into the HA config dir on start.
INTEGRATION_SRC=/opt/atreolink_integration
HA_CONFIG=/homeassistant
INTEGRATION_DEST="${HA_CONFIG}/custom_components/atreolink"
HA_MAIN_CONFIG="${HA_CONFIG}/configuration.yaml"
# Sentinel markers bounding the http: block we manage in configuration.yaml.
TRUST_BEGIN="# >>> atreoLINK managed: reverse-proxy trust (do not edit) >>>"
TRUST_END="# <<< atreoLINK managed: reverse-proxy trust <<<"

# DATA_DIR env wins over YAML and applies before pairing loads, so all state
# (pairing.json, keys, acl, certs) resolves under the persistent /data volume.
export DATA_DIR

log() { echo "[addon] $*"; }

opt()      { jq -r --arg k "$1" '.[$k] // empty' "${OPTIONS}"; }
opt_bool() { [ "$(jq -r --arg k "$1" '.[$k] // false' "${OPTIONS}")" = "true" ] && echo true || echo false; }
opt_has()  { [ -n "$(jq -r --arg k "$1" '.[$k] // empty' "${OPTIONS}")" ]; }

# Emit a YAML list from a string-array option; `[]` when empty (never null).
emit_list() {
    local key="$1" yaml="$2" items
    items="$(jq -r --arg k "${key}" '.[$k] // [] | .[]' "${OPTIONS}")"
    if [ -z "${items}" ]; then
        echo "  ${yaml}: []"
    else
        echo "  ${yaml}:"
        printf '%s\n' "${items}" | while IFS= read -r v; do echo "    - \"${v}\""; done
    fi
}

render_config() {
    {
        echo "log_level: $(opt log_level)"

        echo "wireguard:"
        echo "  listen_port: $(opt wireguard_listen_port)"
        echo "  firewall_enabled: $(opt_bool wireguard_firewall_enabled)"
        echo "  upnp_enabled: $(opt_bool wireguard_upnp_enabled)"

        if opt_has endpoint_ip; then echo "endpoint_ip: \"$(opt endpoint_ip)\""; fi
        if opt_has endpoint_port; then echo "endpoint_port: $(opt endpoint_port)"; fi

        echo "proxy:"
        echo "  enabled: $(opt_bool proxy_enabled)"
        echo "  http_port: $(opt proxy_http_port)"
        echo "  https_port: $(opt proxy_https_port)"
        echo "  auth_port: $(opt proxy_auth_port)"
        emit_list proxy_trusted_networks trusted_networks
        emit_list proxy_trusted_proxies trusted_proxies

        if opt_has certs_email; then
            echo "certs:"
            echo "  email: \"$(opt certs_email)\""
        fi

        echo "notify:"
        echo "  port: $(opt notify_port)"

        echo "smtp:"
        echo "  enabled: $(opt_bool smtp_enabled)"
        echo "  listen: \"$(opt smtp_listen)\""
        echo "  max_message_bytes: $(opt smtp_max_message_bytes)"
        echo "  rate_per_minute: $(opt smtp_rate_per_minute)"
        echo "  tls_enabled: $(opt_bool smtp_tls_enabled)"
    } > "${CONFIG_FILE}"
}

ha_service() {
    # $1 = service (create|dismiss), $2 = JSON body
    # Always returns 0 — every caller in this file runs under `set -e` and
    # relies on that. Delivery status is instead recorded in HA_SERVICE_OK for
    # callers that need to gate behaviour on whether the call actually landed.
    if curl -fsSL -X POST \
        -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$2" \
        "http://supervisor/core/api/services/persistent_notification/$1" \
        >/dev/null 2>&1; then
        HA_SERVICE_OK=true
    else
        HA_SERVICE_OK=false
        log "WARNING: could not reach the Home Assistant notification API"
    fi
}

notify_pairing() {
    local code="$1" url="$2" message body
    message=$(printf '%s\n\n%s\n\n%s' \
        "An atreoLINK client wants to pair with this agent." \
        "**Pairing code:** \`${code}\`" \
        "[**Approve pairing →**](${url})")
    body=$(jq -n --arg m "${message}" --arg id "${NOTIFY_ID}" \
        '{title: "atreoLINK pairing", message: $m, notification_id: $id}')
    ha_service create "${body}"
    log "pairing notification raised — approve at: ${url}"
}

dismiss_pairing() {
    ha_service dismiss "$(jq -n --arg id "${NOTIFY_ID}" '{notification_id: $id}')"
}

notify_port() {
    local p
    p="$(opt notify_port)"
    [ -n "${p}" ] && echo "${p}" || echo 9876
}

# Copy the bundled integration into the HA config dir on first install or when
# the bundled version changes; prompt for a restart when we actually wrote it.
install_integration() {
    [ -d "${INTEGRATION_SRC}" ] || { log "WARNING: integration payload missing at ${INTEGRATION_SRC}"; return 0; }
    if [ ! -d "${HA_CONFIG}" ]; then
        log "WARNING: ${HA_CONFIG} not mounted; skipping integration install"
        return 0
    fi

    local src_ver dest_ver action
    src_ver="$(jq -r '.version // empty' "${INTEGRATION_SRC}/manifest.json" 2>/dev/null || true)"
    dest_ver="$(jq -r '.version // empty' "${INTEGRATION_DEST}/manifest.json" 2>/dev/null || true)"

    if [ -n "${dest_ver}" ] && [ "${dest_ver}" = "${src_ver}" ]; then
        log "atreoLINK integration ${dest_ver} already installed"
        return 0
    fi

    action="installed"
    [ -n "${dest_ver}" ] && action="updated"
    log "${action} atreoLINK integration ${src_ver} at ${INTEGRATION_DEST}"
    mkdir -p "${HA_CONFIG}/custom_components"
    rm -rf "${INTEGRATION_DEST}"
    cp -r "${INTEGRATION_SRC}" "${INTEGRATION_DEST}"

    local message body
    message=$(printf '%s\n\n%s' \
        "The atreoLINK integration was ${action} (version ${src_ver})." \
        "**Restart Home Assistant** to finish setting it up. It is then discovered automatically; if not, add it via Settings → Devices & services → Add integration → atreoLINK.")
    body=$(jq -n --arg m "${message}" --arg id "${INTEGRATION_NOTIFY_ID}" \
        '{title: "atreoLINK integration", message: $m, notification_id: $id}')
    ha_service create "${body}"
}

# --- Reverse-proxy trust (configuration.yaml) --------------------------------
# Home Assistant rejects requests coming from the add-on's built-in reverse
# proxy unless the proxy is listed as trusted. The add-on shares the host
# network, so HA sees those requests from loopback — trusting 127.0.0.1/::1 is
# sufficient and safe (loopback is not remotely reachable).
#
# configuration.yaml can contain custom !include/!secret tags, so we never parse
# it: we append a clearly-marked http: block and remove it on opt-out. If the
# user already has their own top-level http:, we cannot add a second one without
# a duplicate-key error, so we leave it alone and tell them what to add.

# Keep one pristine backup from before we first touched the file.
backup_ha_config() {
    local bak="${HA_MAIN_CONFIG}.atreolink.bak"
    [ -f "${bak}" ] || cp "${HA_MAIN_CONFIG}" "${bak}"
}

notify_proxy_trust() {
    # $1 = markdown message body
    local body
    body=$(jq -n --arg m "$1" --arg id "${PROXY_TRUST_NOTIFY_ID}" \
        '{title: "atreoLINK reverse-proxy trust", message: $m, notification_id: $id}')
    ha_service create "${body}"
}

append_proxy_trust() {
    backup_ha_config
    {
        printf '\n%s\n' "${TRUST_BEGIN}"
        printf 'http:\n'
        printf '  use_x_forwarded_for: true\n'
        printf '  trusted_proxies:\n'
        printf '    - 127.0.0.1\n'
        printf '    - ::1\n'
        printf '%s\n' "${TRUST_END}"
    } >> "${HA_MAIN_CONFIG}"
    log "added reverse-proxy trust block to configuration.yaml"
    notify_proxy_trust "$(printf '%s\n\n%s' \
        "atreoLINK added an \`http:\` block to \`configuration.yaml\` so Home Assistant trusts its built-in reverse proxy." \
        "**Restart Home Assistant** to apply — remote access through the atreoLINK tunnel is then accepted.")"
}

# Remove the block between our markers, then trim any trailing blank lines left
# behind (our block is appended at EOF, preceded by one blank line).
remove_proxy_trust() {
    grep -qF "${TRUST_BEGIN}" "${HA_MAIN_CONFIG}" || return 0
    backup_ha_config
    local tmp
    tmp="$(mktemp)"
    awk -v b="${TRUST_BEGIN}" -v e="${TRUST_END}" '
        $0 == b { skip = 1; next }
        skip && $0 == e { skip = 0; next }
        !skip { lines[n++] = $0 }
        END {
            while (n > 0 && lines[n-1] ~ /^[[:space:]]*$/) n--
            for (i = 0; i < n; i++) print lines[i]
        }
    ' "${HA_MAIN_CONFIG}" > "${tmp}"
    cat "${tmp}" > "${HA_MAIN_CONFIG}"
    rm -f "${tmp}"
    log "removed reverse-proxy trust block from configuration.yaml (opt-out)"
    notify_proxy_trust "$(printf '%s\n\n%s' \
        "atreoLINK removed its managed \`http:\` reverse-proxy trust block from \`configuration.yaml\`." \
        "**Restart Home Assistant** to apply.")"
}

# Ensure Home Assistant trusts the built-in reverse proxy. Idempotent; honours
# the ha_trust_proxy option (opt-out removes our block).
configure_ha_proxy_trust() {
    if [ ! -d "${HA_CONFIG}" ]; then
        log "WARNING: ${HA_CONFIG} not mounted; skipping reverse-proxy trust setup"
        return 0
    fi
    if [ ! -f "${HA_MAIN_CONFIG}" ]; then
        log "WARNING: ${HA_MAIN_CONFIG} not found; skipping reverse-proxy trust setup"
        return 0
    fi

    if [ "$(opt_bool ha_trust_proxy)" != "true" ]; then
        remove_proxy_trust
        return 0
    fi

    # Idempotent: our block is already present.
    if grep -qF "${TRUST_BEGIN}" "${HA_MAIN_CONFIG}"; then
        log "reverse-proxy trust already configured in configuration.yaml"
        return 0
    fi

    # A pre-existing top-level http: block cannot coexist with a second one.
    if grep -Eq '^http:([[:space:]]|$)' "${HA_MAIN_CONFIG}"; then
        log "existing http: block found in configuration.yaml; leaving it untouched"
        notify_proxy_trust "$(printf '%s\n\n%s\n\n%s' \
            "atreoLINK left the existing \`http:\` block in \`configuration.yaml\` untouched." \
            "To reach Home Assistant through the atreoLINK tunnel, add \`127.0.0.1\` and \`::1\` to \`http.trusted_proxies\` and set \`use_x_forwarded_for: true\`, then **restart Home Assistant**." \
            "Set the \`ha_trust_proxy\` add-on option off to silence this reminder.")"
        return 0
    fi

    append_proxy_trust
}

# Hand the key to the integration via Supervisor discovery. Re-published every
# start so a rotated key updates the config entry in place. Non-fatal: if the
# Supervisor rejects the service, the user adds the integration manually.
publish_discovery() {
    local key="$1" port payload
    port="$(notify_port)"
    payload=$(jq -n --arg h 127.0.0.1 --argjson p "${port}" --arg k "${key}" \
        '{service: "atreolink", config: {host: $h, port: $p, api_key: $k}}')
    if curl -fsSL -X POST \
        -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${payload}" \
        "http://supervisor/discovery" >/dev/null 2>&1; then
        log "published atreoLINK discovery to the Supervisor"
    else
        log "note: Supervisor discovery unavailable; add the integration manually"
    fi
}

# One-time nudge to add Home Assistant as an atreoLINK app, raised once pairing
# has produced a device ID. The sentinel lives on the persistent /data volume,
# so it survives restarts and upgrades and this fires exactly once.
#
# Explicit `if` blocks throughout: under `set -e`, a bare `[ test ] && cmd`
# whose test is false returns non-zero and would kill this subshell.
notify_add_ha_app() {
    if [ -e "${APP_PROMPT_SENTINEL}" ]; then
        return 0
    fi

    local device_id="" url message body
    for _ in $(seq 1 60); do
        if [ -s "${PAIRING_FILE}" ]; then
            device_id="$(jq -r '.device_id // empty' "${PAIRING_FILE}" 2>/dev/null || true)"
            if [ -n "${device_id}" ]; then
                break
            fi
        fi
        sleep 1
    done

    # Still unpaired: stay silent and try again on the next start. No sentinel is
    # written, so pairing later still gets the nudge.
    if [ -z "${device_id}" ]; then
        return 0
    fi

    # device_id comes from pairing.json, which originates from atreoLINK — a
    # component this project's threat model explicitly distrusts. It's
    # interpolated into a markdown link below; jq --arg protects the JSON
    # layer but not the markdown layer, so reject anything that isn't a plain
    # identifier before it reaches the URL. No sentinel is written, so a
    # corrected value can still succeed on a later start.
    if ! printf '%s' "${device_id}" | grep -Eq '^[A-Za-z0-9_-]{1,64}$'; then
        log "WARNING: pairing.json device_id has an unexpected format; not raising the add-app notification"
        return 0
    fi

    url="${ATREOLINK_APP_URL}/servers/${device_id}/manage#addApp=${ADD_APP_PRESET}"
    message=$(printf '%s\n\n%s' \
        "Add Home Assistant as an app in atreoLINK so you can reach it remotely." \
        "[**Add Home Assistant →**](${url})")
    body=$(jq -n --arg m "${message}" --arg id "${ADD_APP_NOTIFY_ID}" \
        '{title: "Add Home Assistant to atreoLINK", message: $m, notification_id: $id}')
    ha_service create "${body}"

    # Only mark this done once delivery is confirmed. If the Supervisor call
    # failed, no sentinel is written, so the next start retries the nudge.
    if [ "${HA_SERVICE_OK}" = true ]; then
        : > "${APP_PROMPT_SENTINEL}"
        log "raised the one-time 'add Home Assistant to atreoLINK' notification"
    else
        log "deferring the 'add Home Assistant to atreoLINK' notification; will retry next start"
    fi
}

# The agent writes the key shortly after its notify server boots. Poll briefly,
# then hand it to the integration. The key is never logged — an admin who needs
# it reads it from the atreoLINK dashboard.
watch_api_key() {
    local key
    for _ in $(seq 1 60); do
        if [ -s "${KEY_FILE}" ]; then
            key="$(cat "${KEY_FILE}")"
            publish_discovery "${key}"
            return 0
        fi
        sleep 1
    done
    log "WARNING: ${KEY_FILE} did not appear within 60s; check the agent log"
}

# Strip leading/trailing whitespace without touching URL characters.
trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "${s}"
}

# Tee agent output to the log; raise the notification once code + URL are seen.
watch_pairing() {
    local code="" url="" notified=false line
    while IFS= read -r line; do
        printf '%s\n' "${line}"
        case "${line}" in
            *"Pairing code:"*)
                code="$(trim "${line#*Pairing code:}")"
                ;;
            *"Approve at:"*)
                # Keep the URL verbatim incl. its #fragment.
                url="$(trim "${line#*Approve at:}")"
                ;;
            *"Pairing state saved"*)
                if [ "${notified}" = true ]; then dismiss_pairing; fi
                code=""; url=""; notified=false
                # Pairing just completed: fire the add-app nudge now instead
                # of waiting on the next restart's startup poll. Backgrounded
                # so it cannot block this log-reading loop. A race with the
                # startup poll (still running from main()) is benign: the
                # sentinel check makes this idempotent, and both paths share
                # ADD_APP_NOTIFY_ID, so Home Assistant replaces rather than
                # duplicates the notification.
                notify_add_ha_app &
                ;;
        esac
        if [ "${notified}" = false ] && [ -n "${code}" ] && [ -n "${url}" ]; then
            notify_pairing "${code}" "${url}"
            notified=true
        fi
    done
}

main() {
    [ -f "${OPTIONS}" ] || log "WARNING: ${OPTIONS} not found; rendering from defaults"
    render_config
    log "rendered agent config to ${CONFIG_FILE}"

    install_integration
    configure_ha_proxy_trust

    PIPE="$(mktemp -u)"
    mkfifo "${PIPE}"
    watch_pairing < "${PIPE}" &
    WATCHER=$!

    atreoagent run --config "${CONFIG_FILE}" > "${PIPE}" 2>&1 &
    AGENT=$!

    # Bounded background poll for the key; exits on its own within ~60s.
    watch_api_key &
    KEY_WATCHER=$!

    # Bounded background poll for the pairing device ID; exits on its own.
    notify_add_ha_app &
    APP_WATCHER=$!

    # Forward SIGTERM for a graceful shutdown; loop since it interrupts wait early.
    trap 'kill -TERM "${AGENT}" 2>/dev/null || true' TERM INT
    STATUS=0
    while kill -0 "${AGENT}" 2>/dev/null; do
        wait "${AGENT}" || STATUS=$?
    done

    kill "${WATCHER}" 2>/dev/null || true
    kill "${KEY_WATCHER}" 2>/dev/null || true
    kill "${APP_WATCHER}" 2>/dev/null || true
    rm -f "${PIPE}"
    exit "${STATUS}"
}

# Run only when executed directly, so the script can be sourced in tests.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
