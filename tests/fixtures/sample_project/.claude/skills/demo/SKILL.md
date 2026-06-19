---
name: demo
description: A demonstration skill whose frontmatter description is advertised and always loaded, while this body text loads only when the skill is triggered by the model.
---

# Demo Skill

This body is the on-trigger portion of the skill. It should be counted
separately from the frontmatter description and classified with load timing
"on-trigger", so it never contributes to the resting baseline.

## Usage
- Triggered by intent matching the description above.
- The body stays out of every message until the skill fires.
- Keep the body comprehensive; it is free at rest.
