# Contributing

Contributions are welcome.

## Report an Issue

If you think you've found a bug in the add-on, then please [report an issue](https://github.com/atreoLABS/atreoLINK-HA-Addon/issues/new?assignees=&labels=bug&template=bug_report.md&title=)
using the GitHub issue tracker for the project.

Please provide as much detail as you can and follow the issue template as much as possible.

For **security vulnerabilities**, do not open a public issue — see [SECURITY.md](SECURITY.md).

## Documentation Issues

If you've found an issue with the documentation, or would like to improve it in any way, then
we encourage that you don't open an issue, and instead submit a pull request with your proposed changes.

Our documentation is written in Markdown and GitHub has a built-in editor for markdown files. Just find
the file you want to amend, and click the edit button. GitHub will then guide you through the process of
submitting your change to the project.

## Request a Feature

Before submitting a Pull Request with a new feature, we suggest that you first [propose the feature](https://github.com/atreoLABS/atreoLINK-HA-Addon/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=)
in the issue tracker. This will allow us to discuss your feature request and decide whether or not
we think it's right for the project.

## Development setup

Requirements: [uv](https://docs.astral.sh/uv/) for the bundled Python integration and its tests. Optional, for end-to-end testing: Docker and a Home Assistant OS / Supervised host. The add-on has two code surfaces: the bundled integration (`custom_components/atreolink`) and the add-on entrypoint (`image/run.sh`) plus its `image/Dockerfile`.

```bash
# Lint + format (ruff; config in pyproject.toml)
uvx ruff check .
uvx ruff format --check .

# Run tests — api.py has no Home Assistant dependency, so the suite runs
# against a throwaway venv without pulling in homeassistant.
uv run --python 3.13 --with aiohttp --with pytest --with pytest-asyncio \
    --no-project pytest tests
```

CI runs `ruff check`, `ruff format --check`, the test suite, hassfest (integration manifest), and the add-on linter. PRs must pass all of these.

### How the image is built

Home Assistant **pulls** a prebuilt image — it never builds anything locally. That
is why `atreoagent/` has no Dockerfile: `config.yaml` just sets `image:`, and the
Supervisor pulls the tag matching the add-on `version`.

CI produces that image with `docker buildx` (`linux/amd64` + `linux/arm64`, as a
single multi-arch manifest). It is layered on the published atreoAGENT image and
adds only the Home Assistant layer — `bash`/`jq`/`curl`, the bundled integration,
the `run.sh` wrapper, and a reset `ENTRYPOINT` so the wrapper runs instead of the
agent's default. `run.sh` renders the agent config from the add-on options,
installs the integration, and execs `atreoagent run`. Nothing is recompiled.

The base image is pinned to an atreoAGENT minor line in the `AGENT_IMAGE` `ARG`
at the top of [`image/Dockerfile`](image/Dockerfile), so rebuilds track patch
releases but never jump a minor. Moving to a new minor or major is a deliberate
edit there; the add-on `version` is otherwise independent of the agent's.

### Testing an unpublished image

Because `image:` is set, the Supervisor expects to pull it. To test on a Home
Assistant host before publishing, build it locally so Docker finds it by tag — a
locally-present image is used as-is rather than pulled. Build from the repo root
so the Dockerfile can bundle `custom_components/`:

```sh
# on the HA host, from the repo root
docker build -f image/Dockerfile \
  -t ghcr.io/atreolabs/atreolink-ha-addon:0.1.0 .
```

Then add the repo (or copy `atreoagent/` into `/addons`) and install. The tag must
match `version` in `config.yaml`.

Note that `run.sh` only re-copies the bundled integration into the Home Assistant
config directory when the version in `custom_components/atreolink/manifest.json`
changes. When iterating on the integration, bump that version or delete
`/config/custom_components/atreolink/` first, or your changes will not be picked
up.

### Releases

Home Assistant never looks at git tags. The Supervisor clones this repository,
reads `version:` from `atreoagent/config.yaml` on the **default branch**, and
pulls `<image>:<version>`. Our `v*` tags exist only to trigger the publish
workflow.

So the order matters. The moment `main` advertises a new version, the Supervisor
will try to pull an image with that tag, so the image has to exist first:

1. Tag the release and push it: `git tag v0.2.0 && git push origin v0.2.0`. The
   publish workflow builds `<image>:0.2.0` and moves `latest`.
2. Wait for that workflow to finish.
3. Bump `version:` in `atreoagent/config.yaml` to `0.2.0`, and push that to
   `main`.

Do it the other way round and users are offered a version whose image does not
exist yet; installs and updates fail until the build lands.

Pushes to `main` publish a moving `main` tag and never touch `latest`. To try CI
builds on a real instance, point a non-production copy of the repository at them
by setting `version: "main"` in its `config.yaml`.

## Coding standards

### Comments

- Comment only what the code doesn't show. Explain *why*, not *what*. If a reader can see what the code does by reading it, the comment is redundant — delete it.
- Keep comments brief. Prefer a single line. Strip filler, hedging, and restatement. If you find yourself needing a paragraph, the code probably needs refactoring more than it needs a long comment.
- Update or delete existing comments rather than letting them go stale.
- No narrating comments. Lines like `# loop through members` above a `for member in members` are noise.
- Do keep comments that record non-obvious context: tricky invariants, why a workaround exists, references to external specs (RFCs, vendor docs), platform-specific gotchas.

### Tests

- Use [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606) reserved domains (`example.com`, `example.org`) for fixtures. Don't hard-code real domains.
- Tests live under `tests/`.
- New behaviour needs a test. Bug fixes need a regression test.

### Commits

- Make each commit a coherent change. If you produced intermediate "WIP" commits while developing, squash them before opening the PR.
- Commit messages: short subject line, then a body if the *why* needs explaining. Don't paste the diff into the message.

## Pull Requests

- **Document any change in behaviour** — keep [README.md](README.md) and [atreoagent/DOCS.md](atreoagent/DOCS.md) up to date alongside the code change.
- **Branch from `main`** — all PRs target `main`. Use a feature branch.
- **One PR per feature/fix.** If you want to do two things, send two PRs.
- **Pass CI.** PRs that fail ruff, the test suite, hassfest, or the add-on linter will not be merged until they're green.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Reports of unacceptable behaviour go to community@atreolabs.com.

## License

By contributing, you agree that your contribution will be released under the [Apache License 2.0](LICENSE).
