## Summary

<!-- One or two sentences on what this PR does and why. -->

## Motivation

<!-- Linked issue, bug report, or rationale. Why is this change worth making? -->

## Test plan

<!-- How did you verify this? Mention any manual smoke test on a real HA instance. -->

- [ ] `uvx ruff check .` and `uvx ruff format --check .` clean
- [ ] `uv run --python 3.13 --with aiohttp --with pytest --with pytest-asyncio --no-project pytest tests` passes
- [ ] (If touching the integration) validated with hassfest
- [ ] (If touching config.yaml / run.sh) installed and started the add-on on a real HA instance
