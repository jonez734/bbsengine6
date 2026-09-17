## [Unreleased]

### fix(skin/tmpl): revert page-markdown.tmpl extends target from zoid6-page.tmpl to page.tmpl; align block name with parent's {block name="content"}

On 2026-09-07 the `page-markdown.tmpl` extends target was renamed
from `page.tmpl` to `zoid6-page.tmpl` (commit `cb41487`,
`fix(skin, wwworg): ship templates /engine/router.php requires +
change page-markdown.tmpl extends target to zoid6-page.tmpl`). The
rename was framed as a collision-avoidance measure: the legacy
`bbsengine6/www/org/skin/tmpl/page.tmpl` defines
`{block name="content"}` and is the extends target for many legacy
.org templates (`archive-*`, `contact-us`, `dir`, `errormessage`,
`file`, `index`, `pageshort`, `release`, `sidebar`,
`thankyouforregistering`); the rename was supposed to keep both
template trees intact. To make the rename work,
`bbsengine6/www/org/skin/tmpl/Makefile:39` (then-new) added an
rsync that copied `zoid6/shared/skin/tmpl/page.tmpl` to
`$(WWWSTAGEDOCROOT)skin/tmpl/zoid6-page.tmpl`, so the handbook
renderer (`engine/router.php::router_displayMarkdownFile` calling
`\bbsengine6\displaypage($data, 'page-markdown.tmpl', false)`)
could resolve the extends target on the .org vhost.

That rsync was the load-bearing piece, and it isn't reliably
reaching the .org vhost. The handbook renders through
`page-markdown.tmpl` → `zoid6-page.tmpl`, but the latter is missing
on prod, so the Smarty render raises "Unable to load template
'file:zoid6-page.tmpl'" and the chapter body is served as bare
HTML with no bbsengine.org chrome.

The rename was, on inspection, **unnecessary** — and the block
name in `page-markdown.tmpl` was also wrong:

- `bbsengine6/skin/tmpl/page-markdown.tmpl` defined
  `{block name="main"}`. The legacy
  `bbsengine6/www/org/skin/tmpl/page.tmpl` only defines
  `{block name="content"}` and never defines `main`. Smarty's
  inheritance rule: a child block whose name does not match
  any parent block is **ignored**; the parent's default block
  content (`NEEDINFO:content` in this case) renders in its
  place. So even with the extends target resolved correctly,
  the handbook render would show the placeholder, not the
  rendered Markdown body. The `cb41487` rename avoided this
  only by accident — `zoid6-page.tmpl`
  (`zoid6/shared/skin/tmpl/page.tmpl`) defines
  `{block name="main"}` (line 82), so the renamed extends
  target happened to use the matching block name.
- The parallel blurb-rendered-sections template,
  `bbsengine6/skin/tmpl/page-markdown-sections.tmpl`, has been
  extending bare `page.tmpl` the whole time and renders
  successfully on the .org vhost. That template defines
  `{block name="content"}` (the legacy org block) and works
  without renaming. So the renaming pattern was inconsistent
  even at the time it was introduced — `page-markdown-sections.tmpl`
  already extended bare `page.tmpl` successfully because it
  used the matching block name.
- The org vhost's `SMARTYTEMPLATESDIR`
  (`bbsengine6/www/org/config-prod.php:41`) lists
  `DOCUMENTROOT/skin/tmpl/` as the first entry, so bare
  `page.tmpl` resolves to the legacy org layout that ships the
  bbsengine.org chrome (pageheader + topbar + pagefooter).

This commit reverts the rename and aligns the block name with
the parent's `{block name="content"}`, so the handbook chapters
inherit the .org vhost's native `page.tmpl` chrome directly,
with no separate `zoid6-page.tmpl` rsync to keep in lock-step
and with the rendered Markdown body actually replacing the
parent's default block content.

Changes:

- `bbsengine6/skin/tmpl/page-markdown.tmpl:1` —
  `{extends file="zoid6-page.tmpl"}` →
  `{extends file="page.tmpl"}`.
- `bbsengine6/skin/tmpl/page-markdown.tmpl:5` — rename the
  body block from `{block name="main"}` to
  `{block name="content"}` so it replaces the parent
  `page.tmpl`'s `{block name="content"}` body. Without this
  rename, the rendered chapter body would not appear (the
  parent's `NEEDINFO:content` placeholder would render
  instead).
- `bbsengine6/www/org/skin/tmpl/Makefile:39` — drop the
  `$(RSYNC) $(CURDIR)/../../../../../zoid6/shared/skin/tmpl/page.tmpl $(WWWSTAGEDOCROOT)skin/tmpl/zoid6-page.tmpl`
  line. The comment block at lines 8-26 explaining why
  `zoid6-page.tmpl` exists is no longer relevant and is
  trimmed (with the `{block name="main"}` reference at line 10
  corrected to `{block name="content"}` to match the new
  block name); the `page-markdown.tmpl` + `youarehere.tmpl` +
  `teos-breadcrumbs.tmpl` rsyncs (the templates the handbook
  actually needs that don't ship via the .org vhost's primary
  `*.tmpl` rsync) remain.
- `zoid6/shared/skin/tmpl/page.tmpl` and the .org vhost's
  `skin/tmpl/page.tmpl` are unchanged.
