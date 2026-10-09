# agy review - delegation model

Pin the model and provider agy uses so skill reviews run on Claude rather
than inheriting the agent's parent model.

```bash
hermes config set delegation.model claude-sonnet-4.6
hermes config set delegation.provider openrouter
```

- `delegation.model` overrides the subagent model (empty = inherit parent).
- `delegation.provider` resolves credentials for the subagent. `openrouter` is
  the configured provider and publishes Claude; the session carries
  `OPENROUTER_API_KEY`.
- Read back the effective values with `hermes config get delegation.model` and
  `hermes config get delegation.provider`.

## Why Claude here?

The user wants agy reviews delivered by Claude. `hermes config set` is the
supported way to change live config (manual edits to `config.yaml` are
refused). Setting `delegation.model` / `delegation.provider` is the documented
subagent override, so a single pin covers every future agy review.
