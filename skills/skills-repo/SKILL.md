---
name: skills-repo
description: Sync added Hermes skills to the repo and review with agy.
version: 1.0.0
author: Vasudev Kamath
license: MIT
metadata:
  hermes:
    category: skills-repo
    tags: [skills, skills-repo, sync]
---
# Skills Repo Skill

Syncs user-added Hermes skills into a shared repository at `~/devel/hermes-skills` and keeps the agent's `~/.hermes/skills/` load path pointing at the repo through symlinks, then reviews the new skills with agy (powered by Claude). Bundled `hermes-agent/skills` content and `.hermes/scripts` are never touched.

## When to Use
- A new user skill has been added and should be wired into the agent.
- Before a skills review pass with agy.

## Prerequisites
- Shared repo `~/devel/hermes-skills` on branch `main`, with a `skills/`
  directory that will hold each synced skill.
- Agent loads skills from `~/.hermes/skills/<cat>`.
- Live config is changed with `hermes config set`; commits use `git`.

## Procedure
1. List the skill dirs under `~/.hermes/skills/` and separate user stack from the bundled `hermes-agent/skills/`.
2. For each user skill:
   `mv ~/.hermes/skills/<cat> ~/devel/hermes-skills/skills/<cat>`
3. Re-point the load path at the repo:
   `ln -s ~/devel/hermes-skills/skills/<cat> ~/.hermes/skills/<cat>`
   Remove any stale real dir in `~/.hermes/skills/<cat>` first when the canonical copy already lives in the repo.
4. Leave `.hermes/scripts` exactly as it was (bpfcc monitor scripts keep their existing links).
5. Commit the new skill to the repo:
   `git -C ~/devel/hermes-skills add skills/<cat> && git commit`
6. Review the skill with agy (Claude) before declaring done.

## Quick Reference
- Repo skills dir: `~/devel/hermes-skills/skills/`
- Symlink target: `~/.hermes/skills/<cat>` -> repo `skills/<cat>`
- Review model: `hermes config set delegation.model claude-sonnet-4.6`
- Review provider: `hermes config set delegation.provider openrouter`

## Verification
- `git -C ~/devel/hermes-skills status --short` shows the synced skill.
- `readlink ~/.hermes/skills/<cat>` resolves to the repo path for each item.

## Pitfalls
- Check for a skill under `.hermes/skills/<cat>`, never under `.hermes/`:
  the earlier loop cd'd into `.hermes/` and reported every Debian category as
  missing, so nothing moved. Always anchor to the load dir.
- Do not link scripts to a path outside the hermes folder; the earlier link
  failed because the target sat outside `.hermes/`. Leave `.hermes/scripts`
  alone.
- Review after the symlink exists; a pre-link edit hides the deployed path.
  Verify each link resolves with `readlink` before completing.

## References
- `references/delegation-model.md` - pinning agy to Claude and reading the
  effective values back.
