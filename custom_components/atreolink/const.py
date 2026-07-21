"""Constants for the atreoLINK integration."""

from __future__ import annotations

DOMAIN = "atreolink"

# Discovery config keys (published by the add-on to the Supervisor and also
# accepted on the manual config-flow step).
CONF_HOST = "host"
CONF_PORT = "port"
CONF_API_KEY = "api_key"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876

# How often the member roster is refreshed from the agent.
UPDATE_INTERVAL_SECONDS = 60

# Generic service exposed for templated / multi-recipient notifications.
SERVICE_SEND_NOTIFICATION = "send_notification"
ATTR_TARGETS = "target"
ATTR_TITLE = "title"
ATTR_MESSAGE = "message"
ATTR_SEVERITY = "severity"
ATTR_HTML = "html"

SEVERITIES = ["info", "warning", "error"]
DEFAULT_SEVERITY = "info"
