# Install in naflan222/Pixelautomatic from Android

Use this guide only if manually installing the standalone package into an empty repository. If the application files and workflows are already visible in Pixelautomatic, skip directly to the main README setup. A connected GitHub App must include Pixelautomatic in its selected repository access to install updates; account admin access alone does not grant an integration access.

This installation route uses GitHub's browser editor and a short Codespaces session. Personal accounts may have a free Codespaces allowance; check your account's current included usage first. Do not enable paid usage or enter a payment method for this setup. If you have no free Codespaces allowance, use a computer with Python/git, or upload the extracted files through GitHub's browser editor instead.

## One-file Android installation

1. Download the supplied **`install_pixelhouse.py`** file to your Android Downloads folder. It contains the reviewed source package and no credentials.
2. Open https://github.com/naflan222/Pixelautomatic in Chrome, signed in as the repository owner. Enable **Desktop site** if needed.
3. On the empty repository page, choose **uploading an existing file**. Select `install_pixelhouse.py` and commit it to `main`. If you already created a README, use **Add file → Upload files** instead.
4. Open **Code → Codespaces → Create codespace on main**. Use a standard machine within your included free allowance. Wait for the browser editor to open.
5. Open **Terminal → New Terminal**. The terminal should be in `/workspaces/Pixelautomatic`.
6. Run:

   ```bash
   python install_pixelhouse.py
   ```

   This extracts source code into your repository, including the hidden `.github/workflows` directory. It does **not** create tokens, connect accounts, run publishing, or change the automation-enabled variable.
7. Review the extracted files. Then commit and push:

   ```bash
   git add .
   git commit -m "Add free Pixelhouse Facebook and Instagram automation"
   git push
   ```

   Use the Codespace's own authorized GitHub connection. If GitHub refuses workflow-file writes, correct that connection's permission or add the two workflow files using GitHub's official browser editor; do not share an access token in chat or put one into a source file.
8. Stop the Codespace from its menu, or from https://github.com/codespaces → your Codespace → **Stop codespace**. The pushed source stays in GitHub. You do not keep Codespaces running for scheduled posts.
9. Return to the repository → **Actions**. The **Tests** workflow should run. The marketing workflow remains disabled for scheduled publishing until you enable it in the main README setup.
10. Follow [README.md](../README.md): preview → config/rights confirmation → Meta secrets → initialize → check → enable → test real publishing.

## ZIP / computer alternative

Extract `pixelhouse-facebook-instagram.zip` into a local clone of this repository, then commit and push. The ZIP is flat: `run.py`, `config.json`, `pixelhouse/`, `assets/`, `tests/`, `docs/`, and `.github/` belong at the repository root. Do not put them inside an extra `pixelhouse-facebook-instagram` folder.

On a computer:

```bash
git clone https://github.com/naflan222/Pixelautomatic.git
cd Pixelautomatic
# Extract the supplied ZIP here, including .github.
git add .
git commit -m "Add Pixelhouse automation"
git push
```

Do not upload `.env`, real tokens, personal files, virtual environments, or the output previews as source. The packaged `.env.example` only names the required GitHub Secrets. The automation's marketing media is uploaded later to a separate branch only when you explicitly enable and run publishing.
