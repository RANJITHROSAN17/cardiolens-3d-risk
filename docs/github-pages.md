# GitHub Pages: use, deploy and troubleshoot

## Open and explore

Visit https://ranjithrosan17.github.io/cardiolens-3d-risk/ . The site currently deployed at that URL shows whatever commit was last deployed; this branch's updates are visible there only after deployment. This is a public research demo. Never enter real patient data or identifiers.

1. Read the safety banner. The 10-year prevention section is a planning checklist, not a calculator; checkboxes reset when the page reloads.
2. In the fictional follow-through worklist, use **Stage** to filter, **Advance** or **Back** to move demo cases, and **Reset demo** to restore the examples. Nothing is scheduled, sent or saved.
3. The dataset-test section shows aggregate research results. It does not test the scores below or provide an individual future risk. See [dataset experiment](dataset-experiment.md).
4. In the coronary explorer, select a synthetic case, change inputs and select **Run demo estimate**. Rotate the schematic by dragging; select a vessel to inspect it. Those fabricated 0–1 demo scores do not represent probability, a blockage or future events. No real medical decisions should use them.

## Deployment

The repository's `.github/workflows/pages.yml` builds Vite and deploys to GitHub Pages. On GitHub open **Settings → Pages → Build and deployment → Source → GitHub Actions**. Merge the upgrade branch to `main` after review: pushes to `main` automatically run the workflow. On **Actions → Deploy CardioLens 3D to GitHub Pages**, inspect the run; once deployment succeeds, open the URL above and hard-refresh. If Pages isn't available, check repository visibility, plan and organization permissions. This document does not imply a deployment has already occurred.

The workflow also supports **Run workflow** from Actions if GitHub allows it. Selecting this branch may deploy it directly to the live site, replacing the current deployment; coordinate with the repo owner before doing so. The workflow file must be present on the default branch for GitHub to show a manually runnable workflow. A successful push to a non-main branch alone does not deploy it.

The default build uses `/cardiolens-3d-risk/` as the base path. For a fork or differently named project repository, change `VITE_BASE_PATH` in the workflow to `/<repository-name>/` and use `https://<owner>.github.io/<repository-name>/`. For a user/organization site at the domain root use `/`. Rebuild and redeploy after changing the path. Locally run `npm ci`, then `VITE_BASE_PATH=/ npm run dev` (PowerShell: `$env:VITE_BASE_PATH='/'; npm run dev`), and open Vite's displayed URL.

## API and safety

GitHub Pages hosts static files; it cannot run FastAPI or train a model. With repository variable `VITE_API_BASE_URL` **unset**, the browser uses a fabricated local synthetic demonstration formula. The dataset test is a precomputed aggregate report, not a live model. If an approved separate HTTPS API URL is configured under **Settings → Secrets and variables → Actions → Variables**, it is embedded in the public build and visible to users; never put a secret or token there. Backend hosting, CORS, access control, uptime, privacy and correct API configuration are separate responsibilities. API errors do not trigger a replacement synthetic prediction in the updated code. Never deploy real-patient handling from this prototype.

For missing styles or assets, check base path and workflow logs. For a stale page, confirm the right branch/commit was deployed and refresh. For API errors inspect browser developer tools and server logs without exposing patient data or secrets. Treat leaked GitHub tokens as compromised and revoke them; do not publish credentials in the repository, Actions variables or frontend.
