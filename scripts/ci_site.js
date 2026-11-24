// Run by `wrangler deploy` just before it uploads (the "build" command in the wrangler.jsonc at the
// top of the repository).
//
// Cloudflare builds every Worker that is connected to this repository on every push to main. A Worker
// whose build setting "Root directory" is empty uses that top wrangler.jsonc, which serves site/ (the
// Bible). Cloudflare tells wrangler which Worker it is building in WRANGLER_CI_OVERRIDE_NAME. When that
// Worker is the study site ("analysis", or "study"), this puts site-study/ in the place of site/ in
// Cloudflare's own copy of the repository, so that Worker serves the study site. For the "bible" Worker,
// and anywhere else (a laptop, a cloud session, a GitHub Action), it changes nothing.
//
// It never fails the deploy: on any error it leaves site/ as it is and says so.
const fs = require("fs");
const path = require("path");

const STUDY_WORKERS = ["analysis", "study"];

try {
  const name = process.env.WRANGLER_CI_OVERRIDE_NAME || "";
  if (!STUDY_WORKERS.includes(name)) {
    console.log(`ci_site: Worker "${name || "(not named by Cloudflare)"}" serves site/`);
  } else {
    const root = path.dirname(__dirname);
    const site = path.join(root, "site");
    const study = path.join(root, "site-study");
    const next = path.join(root, "site.next");
    if (!fs.existsSync(path.join(study, "index.html"))) throw new Error("site-study/index.html is missing");
    fs.rmSync(next, { recursive: true, force: true });
    fs.cpSync(study, next, { recursive: true });
    fs.rmSync(site, { recursive: true, force: true });
    fs.renameSync(next, site);
    console.log(`ci_site: Worker "${name}" serves site-study/`);
  }
} catch (e) {
  console.log("ci_site: left site/ as it is (" + e.message + ")");
}
