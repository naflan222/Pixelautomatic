# Obtain authorized Facebook + Instagram access

You only do this initial account setup and occasional reauthorization when Meta invalidates access. The GitHub workflow handles daily posting afterward.

## Your accounts

1. Your Facebook login must have appropriate Page access/control to publish as Pixelhouse.
2. Change Instagram to a professional Business or Creator account if needed.
3. In Meta Business Suite / Page settings, connect that Instagram account to the Pixelhouse Page. This integration uses the **Instagram API with Facebook Login** and expects the Page link.

## Your Meta developer app

1. Sign in at https://developers.facebook.com/apps/ and create/configure an app for your business use case.
2. Enable the relevant Facebook Login for Business and Instagram API publishing products/use cases offered by your app dashboard.
3. For this server-free setup, the GitHub workflow itself does not host an OAuth callback. You authorize your own Page through Meta's official developer tools and place the resulting Page token in GitHub Secrets. Never add an invented callback address or paste credentials into public files.
4. Request the permissions your app's configured login/product supports:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
   - `instagram_basic`
   - `instagram_content_publish`
5. Meta may require app review, advanced access, business verification or app Live mode, depending on the app, roles and accounts. Developer-mode access for app-role accounts is subject to Meta's rules. A token or app ID does not grant permissions that Meta has not approved.

## Get the token and IDs using official tools

On Android, use Chrome's **Desktop site** if the tools are difficult to navigate.

1. Open https://developers.facebook.com/tools/explorer/ and select **your own app**.
2. Authorize the required permissions with the Facebook user that manages the Page.
3. Generate a user token through the official tool. For ongoing use, obtain/extend an eligible long-lived user token using Meta's token tools and documented flow, then obtain the Page token from it. Meta's interface may offer a Get Page Access Token action; inspect the result's validity/lifetime before relying on it.
4. With the authorized user token selected, use the Graph Explorer GET request:

   ```text
   /me/accounts?fields=id,name,access_token,instagram_business_account
   ```

5. Find the **Pixelhouse** Page in the returned data:
   - Its `id` → GitHub secret `FACEBOOK_PAGE_ID`.
   - Its `access_token` → GitHub secret `META_PAGE_ACCESS_TOKEN`.
   - Its `instagram_business_account.id` → GitHub secret `INSTAGRAM_ACCOUNT_ID`.
6. Do not copy another Page's token or the original user token into the Page-token secret. If the Instagram field is absent, verify Page linking, professional-account status and permissions first.
7. Inspect token validity and authorized permissions in https://developers.facebook.com/tools/debug/accesstoken/ . Page tokens derived from suitable long-lived user tokens can have different lifetime behavior; no token is guaranteed never to be invalidated. Follow Meta's current long-lived token documentation, not third-party “permanent token” generators.
8. Add these three values under GitHub repository Settings → Secrets and variables → Actions → Secrets. Do not share the raw response or token in chat.
9. Run the workflow's `check` command. Then, after reviewing previews and flags, enable automation and test a real image and Reel on each selected account.

The workflow verifies that `/me` resolves to the configured Page. If it says “not a Page token”, repeat Page-token extraction; don't disable the check.

## Common failures

| Failure | Check |
|---|---|
| Meta code 190 / invalid token | Validity, expiry and revocation; replace the secret |
| Missing publish permissions | App permissions, business/Page roles, account authorization and required review |
| Instagram not linked | Professional account and Page link; correct numeric account ID |
| Media cannot be fetched | Repository is public, raw media URL is accessible without login, media is valid JPEG/MP4; inspect platform rejection |
| Reel/container still processing | Run `reconcile`; it reuses the recorded media ID |
| Uncertain outcome | Check the actual account before resolving or authorizing a retry |

The application requests no Facebook/Instagram account passwords. App secrets are not needed by the daily workflow once you have supplied an authorized Page token. If you choose Meta's explicit user-token exchange API, keep the app secret server-side/in official tools and out of public URLs, logs and repository files.

## Official references

- Pages access tokens: https://developers.facebook.com/docs/pages/access-tokens/
- Long-lived tokens: https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived/
- Page posts/photos: https://developers.facebook.com/docs/pages-api/posts/
- Facebook Reels: https://developers.facebook.com/docs/video-api/guides/reels-publishing/
- Instagram publishing: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/content-publishing/

The configured Graph version is `v27.0`, as illustrated in the current Meta Reels documentation checked during implementation. Verify availability and your app's permission/product setup at launch and when upgrading Graph versions. Official APIs, app approval and access-token invalidation rules can change.
