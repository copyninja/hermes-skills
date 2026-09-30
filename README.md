# hermes-skills

Sharable Hermes Agent skills and scripts for Debian package monitoring and similar workflows.

## Install

```bash
# Clone
git clone <repo> ~/devel/hermes-skills

# Symlink skills into ~/.hermes/skills
ln -sfn ~/devel/hermes-skills/skills/debian-package-maintenance ~/.hermes/skills/debian-package-maintenance

# Symlink scripts into ~/.hermes/scripts
ln -sfn ~/devel/hermes-skills/scripts ~/.hermes/scripts/debian-monitors
```

Then restart Hermes or reload skills.

## Contents

- skills/debian-package-maintenance/
  - SKILL.md
  - debian-package-monitor/SKILL.md
  - references/
- scripts/
  - bpfcc-unstable-monitor.sh
  - bpfcc-exp-monitor.sh

No secrets included. API keys are read from keyring at runtime.
