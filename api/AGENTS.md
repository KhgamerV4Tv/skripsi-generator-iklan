# API Guidance

- Keep external-service integrations isolated in this folder.
- Credentials must be passed by the caller; never hard-code keys or print them.
- Use bounded timeouts, validate provider responses, and return privacy-safe errors.
- Network-backed tests must be opt-in; default tests should not call live services.
