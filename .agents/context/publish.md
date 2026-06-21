Weekly Publishing Workflow
==========================

The end-to-end pipeline from raw feeds to a Substack draft ready for the user to
publish.

Phase 1 — Generate
------------------
```
uv run dev-digest run -d --no-ai --days 7 -wf
```
Writes `out/<YYYY-MM-DD>/dev_digest_newsletter_<YYYY_MM_DD>.md` + diagnostics.

Phase 2 — Curate
----------------
Walk the user through the markdown file section by section. Apply the rules in
`editorial.md` before suggesting any cuts or section moves. The output should
be:

- 2 strong top picks (Interesting Reads) with host diversity.
- RA classified by severity, regional / partner noise removed.
- Security: incident-driven only.
- Each thematic section trimmed to high-signal items.
- ML & AI: aggressively cut policy / consumer / PR noise.
- Misc: a place for high-signal items that overflow other sections.

When the user approves, edit the markdown directly. Do not write the curation
to a new file — overwrite the generated markdown in place.

Phase 3 — Convert
-----------------
```
uv run dev-digest publish out/<YYYY-MM-DD>/dev_digest_newsletter_<YYYY_MM_DD>.md
```
Writes `<same-dir>/<same-name>.html`. The converter:
- Maps `## Section` → `<h2>`, `### Subsection` → `<h3>`.
- Bold item bullets become `<li><a href="URL"><strong>Title</strong></a> — date: desc.</li>` (the trailing "Read: URL" is dropped).
- RA date bullets become `<li>date — <a href="URL">Title</a></li>`.
- Footer markdown links become `<a>` tags; the heart emoji is preserved.

Phase 4 — Publish to Substack (Playwright)
------------------------------------------
The full sequence below. Pre-condition: `.mcp.json` configures the Playwright
MCP server with `--user-data-dir $HOME/.playwright-profiles/substack` so the
Substack session persists. If you're not logged in, the user must do it once
manually in the browser the MCP server launches.

**ALWAYS stop before clicking "Send to everyone now"**. The user verifies and
publishes manually.

### Step 1 — Navigate to dashboard
```
browser_navigate → https://weirdion.substack.com/publish/home
```

### Step 2 — Create new article

**Preferred (more reliable):** navigate directly to the new-post URL. Substack
creates a fresh draft and redirects to `/publish/post/<id>`:
```
browser_navigate → https://weirdion.substack.com/publish/post?type=newsletter
```

**Fallback:** click through the Create dropdown. Note: the dropdown sometimes
fails to render the "Article" menu item after `Create` is clicked (seen
2026-06-21). Use the direct URL above if this happens.
```
browser_click → text=Create
browser_click → text=Article
```

### Step 3 — Set section
```
browser_click → text=Choose a section
browser_click → text=Developer Newsletter
browser_evaluate → () => document.querySelector('.file-sidebar-header-button')?.click()
```
The last line closes the sidebar that opens after section selection.

### Step 4 — Fill title and subtitle
```
browser_type → [data-testid="post-title"]
  text: "Dev Digest — Week of YYYY-MM-DD"

browser_type → [placeholder="Add a subtitle…"]
  text: "Aggregated tech stuff that happened this week without the marketing noise."
```

### Step 5 — Paste HTML body
Read the HTML file from disk, inline it into the JS template literal, and
write it to the clipboard as `text/html`:

```
browser_evaluate →
  const html = `<paste contents of the HTML file>`;
  const blob = new Blob([html], { type: 'text/html' });
  return navigator.clipboard.write([new ClipboardItem({ 'text/html': blob })]);

browser_click → [data-testid="editor"]
browser_press_key → Meta+v
browser_wait_for → time: 3
```

Substack's ProseMirror editor parses `<h2>`, `<h3>`, `<ul>`, `<li>`,
`<strong>`, `<a href>` correctly. Plain-text markdown paste does NOT work.
Escape `&` to `&amp;` in section headings to avoid sniff edge cases (the
converter already produces raw `&` and it has worked, but be defensive).

### Step 6 — Open publish dialog
```
browser_click → button:has-text("Continue")
browser_wait_for → time: 2
```
This opens the "Publish" modal with Audience / Comments / Section / Tags /
Social preview / Delivery.

### Step 7 — Add tags
The standardized list is `SUBSTACK_TAGS` in
`src/dev_digest/utility/constants.py` (34 tags, applied to every post).

The combobox needs to be in "open" state. The most reliable way:

```
browser_type → [placeholder="Select or create tags"]
  text: "AWS"
  submit: true
```

This adds the first tag AND opens the dropdown (the listbox renders all 69+
existing options). Then batch-click the remaining 33:

```
browser_evaluate →
  const targets = ['DevOps', 'Kubernetes', 'Security', 'Python', 'IaC',
    'Containers', 'News', 'ML', 'MLOps', 'Agentic AI', 'AI', 'Bedrock', 'CDK',
    'CI/CD', 'CLI', 'Claude', 'Cloud Engineering', 'Data Engineering',
    'Data Pipeline', 'developers', 'Disaster Recovery', 'ETL', 'GenAI',
    'Gemini', 'Github', 'GPT', 'Infrastructure As Code', 'SageMaker',
    'Serverless', 'Software Engineering', 'software development', 'technology',
    'Terraform'];
  const clicked = [], missing = [];
  for (const t of targets) {
    const opt = [...document.querySelectorAll('[role="option"]')]
      .find(o => o.textContent.trim() === t);
    if (opt) { opt.click(); clicked.push(t); } else { missing.push(t); }
  }
  return { clicked: clicked.length, missing };
```

**TRUST the `clicked: N` return value.** Tags are saved server-side even if
the chip UI doesn't fully re-render. DO NOT retry — the second batch triggers
Substack's "Tag already set" alert flood which floods the dialog state and
takes many `browser_handle_dialog` calls to drain.

If the user wants to verify the chips, they can refresh the page and reopen
the Publish dialog — all 34 chips will render correctly from server state.

### Step 8 — Set social preview cover image

**DO NOT press Escape** to close the tag dropdown — it closes the entire
Publish dialog and you'll have to click Continue again. Instead, click the
dialog heading (a neutral element) to dismiss the dropdown, then click the
Social preview button:

```
browser_evaluate →
  document.querySelector('[role="dialog"] h2')?.click();
  const dlg = document.querySelector('[role="dialog"]');
  const btns = [...dlg.querySelectorAll('button')];
  const social = btns.find(b =>
    b.textContent.includes('Dev Digest') &&
    b.textContent.includes('substack.com'));
  if (social) social.click();
```

A sub-dialog "Edit social preview" opens. Two image thumbnails appear at the
bottom; the first is the newsletter cover (developer at laptop). Click it:

```
browser_evaluate →
  const imgs = document.querySelectorAll('dialog img, [role="dialog"] img');
  const btn = imgs[0].closest('[role="button"],button,a');
  (btn || imgs[0]).click();
```

Then save:
```
browser_click → text="Save"
```
(Use exact match. The button labeled "Saved" — the autosave status indicator —
will match a non-exact selector.)

### Step 9 — STOP

Take a screenshot to confirm everything is set:
- ✅ Section: Developer Newsletter
- ✅ Audience: Everyone
- ✅ Comments: Everyone
- ✅ Tags: AWS + Serverless chips visible (other 32 saved server-side)
- ✅ Social preview shows correct title + subtitle + cover image
- ✅ "Send to everyone now" button is present and enabled

Hand off to the user. Do NOT click "Send to everyone now". Delete any
screenshot artifacts (`*.png`) before ending the session — `.playwright-mcp/`
is already gitignored.

Known symptoms and how to interpret them
----------------------------------------
- **Only 2 tag chips visible after batch-click** — expected. Tags are saved
  server-side. Refresh + reopen Publish dialog to verify chip rendering.
- **"Tag already set" alert appears** — you retried a tag that the previous
  batch already added. Stop, do not click any more options, dismiss the alert
  with `browser_handle_dialog`, and trust the original batch's result.
- **Continue button can't be found after Escape** — Escape closed the Publish
  dialog. Re-click Continue.
- **Tags dropdown won't open by clicking the combobox alone** — type one tag
  first (`AWS` + Enter). This both adds the tag and forces the listbox open
  with all 69+ options for the subsequent batch click.
- **Cover image not auto-selected** — Substack picks one of the two
  thumbnails on first publish; you have to explicitly click the first
  thumbnail to set the developer-at-laptop cover for the newsletter brand.
