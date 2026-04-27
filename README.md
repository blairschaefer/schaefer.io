# schaefer.io

Personal site, deployed via Cloudflare Pages from this repo.

The site rotates its color palette and typography automatically once a day. A GitHub Actions workflow asks Claude to pick from a curated set of options (defined in `theme.json`) and writes the result to `theme.css`. The HTML/structure is never touched by automation.

## Files

| File | Purpose | Touched by automation? |
|---|---|---|
| `index.html` | Site structure & layout | No |
| `avatar.png` | Profile image | No |
| `theme.css` | Active colors & fonts (CSS variables) | **Yes** — overwritten daily |
| `theme.json` | Curated palettes & font pairings (the variation space) | No |
| `theme-history.json` | Record of recent selections | **Yes** — appended daily |
| `scripts/update_theme.py` | The rotation script | No |
| `.github/workflows/daily-theme.yml` | Daily cron workflow | No |

## One-time setup

1. **Get an Anthropic API key.** Sign up at <https://console.anthropic.com>, add a small amount of credit ($5 lasts a long time at this usage level — daily runs cost a fraction of a cent each), and create an API key.

2. **Add it as a GitHub secret.** In this repo on GitHub: Settings → Secrets and variables → Actions → New repository secret. Name: `ANTHROPIC_API_KEY`. Value: the key from step 1.

3. **Verify GitHub Actions has write permission.** Settings → Actions → General → Workflow permissions → "Read and write permissions" must be selected.

4. **Test it manually before letting the cron take over.** Actions tab → "Daily Theme Rotation" → "Run workflow". Watch it run, then check that `theme.css` was updated and the site still looks right after Cloudflare Pages redeploys (usually within a minute or two of the commit).

## Editing the variation space

Open `theme.json`. Add, remove, or tweak palettes and fonts however you like. As long as the field names stay the same, the script will pick them up on the next run. New palettes/fonts take effect immediately — no code changes needed.

## Manual edits to the site

When you edit the site by hand, just commit normally. The next scheduled run will detect that the most recent commit wasn't a theme rotation and **skip itself**, so your edits are never clobbered. Theme rotation resumes the day after that.

If you want to force a theme rotation right after a manual commit, trigger the workflow manually from the Actions tab.

## Rolling back a theme you don't like

Each rotation is a single commit modifying only `theme.css` and `theme-history.json`. To revert: `git revert <commit-sha>` and push, or just trigger another manual run.

## Disabling the automation

Comment out the `schedule:` block in `.github/workflows/daily-theme.yml`, or disable the workflow in the Actions tab. No other changes needed — the site continues to work with whatever `theme.css` was last in place.
