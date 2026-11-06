# Pixelhouse automation maintenance

This is the focused, server-free Python edition. Do not add a database or always-on worker dependency without changing the deployment instructions.

- Publish only through official authorized Meta APIs.
- Keep tokens in GitHub Actions Secrets. Never commit tokens or account passwords.
- Do not remove durable pre-request checkpoints or replay uncertain submissions.
- Preserve posting history and content-addressed media on automation-state.
- Reverify price, name, photograph and stock before each final publication action.
- Keep preview safe and publishing disabled until the owner enables it.
- Tests must use mocked Meta responses and synthetic imagery, never live posting credentials.
- Keep config examples valid and Android setup instructions accurate.
