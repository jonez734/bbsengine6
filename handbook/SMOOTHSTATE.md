# Smoothstate: AJAX Page Transitions

## Overview

Smoothstate.js is a jQuery plugin that creates smooth CSS-based page transitions. Instead of hard page reloads with white flashes, users experience fade-in/fade-out animations while content loads via AJAX.

**Status:** ✅ Currently working in asimov. Available for rollout to other bbsengine6-based sites.

## How It Works

### Basic Flow

1. User clicks a navigation link
2. Smoothstate intercepts the click and shows exit animation (fade out)
3. New page content loads in the background via AJAX
4. Exit animation completes (250ms)
5. New content is injected into the DOM
6. Entry animation plays (fade in)
7. History is updated (HTML5 pushState for back/forward support)

### Animation Lifecycle

```
User clicks link
    ↓
onStart callback fires (250ms exit animation)
    → toggleAnimationClass("is-exiting") 
    → #head and #body fade out
    ↓
AJAX request in background
    ↓
Content arrives
    ↓
onReady callback (if defined)
    → New content injected
    → fadeIn class triggers entry animation
    ↓
Complete - user sees smooth transition
```

## Configuration

### Default Settings

Configuration is defined in `/bbsengine6/js/initsmoothstate.js`:

```javascript
var SmoothStateConfig = {
  debug: true,              // Console logging enabled
  prefetch: true,           // Pre-load pages on hover
  cacheLength: 2,           // Pages to keep in memory
  onStart: {
    duration: 250           // Exit animation duration (ms)
  }
};
```

### Per-Site Customization

Sites can override these settings in their `page.tmpl` with a JavaScript override before loading initsmoothstate.js:

```html
<script>
  // Custom config for this site
  window.SmoothStateConfig = {
    debug: false,
    prefetch: false,  // Don't prefetch on this page
    cacheLength: 1,
    onStart: {
      duration: 500
    }
  };
</script>
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>
```

### Which Initialization Script to Use

**Use `/bbsengine6/js/initsmoothstate.js`** - This is the recommended initialization script for all sites.

It provides:
- ✅ Minimal footprint (19 lines)
- ✅ Standard defaults proven in production
- ✅ Support for runtime configuration via `SmoothStateConfig` object
- ✅ Clear error messages in console

All sites in the inheritance chain (asimov, achilles, empyre, rgs) use this script successfully.

## Available Animations

The entry animation is controlled by the CSS class applied to the body during page entry. Available animations (from `animate.css`):

| Animation | Effect |
|-----------|--------|
| `fadeIn` (default) | Smooth opacity fade from 0 to 1 |
| `slideInLeft` | Slide in from left edge |
| `slideInRight` | Slide in from right edge |
| `slideInUp` | Slide up from bottom |
| `slideInDown` | Slide down from top |
| `zoomIn` | Scale from small to full size |
| `rotateIn` | Rotate into view |
| `bounceIn` | Bounce into view |
| `rollIn` | Roll into view |

To use a different animation, modify the body element class or update the initialization script:

```html
<body id="body" class="scene element slideInLeft">
  <!-- page content -->
</body>
```

The exit animation (fade out) is controlled by the `is-exiting` CSS class toggle mechanism defined in the onStart callback.

## Required HTML Structure

### Body Element

The body element **must** have these attributes and classes:

```html
<body id="body" class="scene element fadeIn">
  <!-- page content -->
</body>
```

**Why each is required:**
- `id="body"` - Smoothstate selector to target for content replacement
- `class="scene"` - Marks this as an animated container
- `class="element"` - Marks element as ready for animation
- `class="fadeIn"` - Initial entry animation class

### Head Element

The head element must have `id="head"`:

```html
<head id="head" itemscope itemtype="https://schema.org/WebSite">
  <!-- meta tags, styles, scripts -->
</head>
```

Smoothstate updates the head when pages load to handle meta tags, titles, and other document properties.

## Required CSS & Dependencies

**Important:** All script paths must use Smarty constant `{$smarty.const.ENGINEURL}` which resolves to `/engine/` in production. See asimov/www/skin/tmpl/page.tmpl for working examples.

### 1. jQuery 3.7.1+

```html
<script src="https://code.jquery.com/jquery-3.7.1.min.js" crossorigin="anonymous"></script>
```

### 2. Smoothstate Plugin

```html
<script defer src="{$smarty.const.ENGINEURL}js/jquery.smoothState.js"></script>
```

**File Location:** `/bbsengine6/js/jquery.smoothState.js` (source) → served at `/engine/js/` (production via Smarty constant)

### 3. Smoothstate Initialization

```html
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>
```

**File Location:** `/bbsengine6/js/initsmoothstate.js` (source) → served at `/engine/js/` (production via Smarty constant)

The bbsengine6 initialization script provides all core functionality with sensible defaults:
- `debug: true` - Console logging enabled (can be overridden)
- `prefetch: true` - Pre-load pages on hover
- `cacheLength: 2` - Keep 2 pages in memory
- `onStart.duration: 250` - Exit animation duration (250ms)

### 4. CSS Animations

The site must load `animate.css` which provides the animation classes:

```html
<link rel="stylesheet" type="text/css" href="{$smarty.const.ENGINESKINURL}css/animate.css">
```

**Animation Classes Used:**
- `.fadeIn` - Entry animation (opacity 0→1)
- `.is-exiting` - Exit animation (applied during transition)

## Enabling Smoothstate for a Site

### Using the Inheritance Chain

The inheritance path for `page.tmpl` is: **zoid6 shared → local site (with overrides only)**

**Default Strategy (Recommended):**
- Sites should use the shared zoid6 version: `/zoid6/shared/skin/tmpl/page.tmpl`
- Do NOT create a local `page.tmpl` unless your site has specific customizations

**Only Create a Local page.tmpl If:**
- Your site requires custom styling, layout, or functionality in the template
- You cannot accomplish your goal with the shared template's block overrides
- Document clearly why the local version is needed

**If your site has a local page.tmpl:**
- Ensure it's based on zoid6's shared template: `/zoid6/shared/skin/tmpl/page.tmpl`
- Verify it includes all required smoothstate elements (see checklist below)

### Checklist

**If site has NO local page.tmpl overrides (default approach):**
- [ ] Site uses shared template: `/zoid6/shared/skin/tmpl/page.tmpl` ✅ (smoothstate already configured)
- [ ] Verify smoothstate loads correctly in browser DevTools
- [ ] Test in multiple browsers (Chrome, Firefox, Safari, Edge)

**If site HAS a local page.tmpl with customizations:**
- [ ] Local `page.tmpl` is based on `/zoid6/shared/skin/tmpl/page.tmpl`
- [ ] Site's `page.tmpl` loads jQuery 3.7.1+
- [ ] Site's `page.tmpl` loads `jquery.smoothState.js` from `{$smarty.const.ENGINEURL}js/jquery.smoothState.js` (with `defer` attribute)
- [ ] Site's `page.tmpl` loads `initsmoothstate.js` from `{$smarty.const.ENGINEURL}js/initsmoothstate.js` (with `defer` attribute)
- [ ] Site's `page.tmpl` loads `animate.css`
- [ ] Body element has `id="body"` and `class="scene element fadeIn"`
- [ ] Head element has `id="head"`
- [ ] Scripts loaded in correct order: jQuery → smoothState plugin → initsmoothstate.js
- [ ] Site tested in modern browsers (IE 10+, all current browsers)

### Implementation Example

**Default: Use the Shared zoid6 Template**

For most sites, simply use the shared template without creating a local copy:

```
Site Configuration:
├── Inherited from zoid6/shared/skin/tmpl/page.tmpl ✅ (smoothstate configured)
├── No local page.tmpl needed
└── Block overrides in individual content templates as needed
```

**Reference: Shared zoid6 Template** (`/zoid6/shared/skin/tmpl/page.tmpl`):

```html
<!DOCTYPE html>
<html lang="en-us" id="html">
<head id="head" itemscope itemtype="https://schema.org/WebSite">
{block name="head"}
<meta charset="utf-8">
<link rel="stylesheet" type="text/css" href="{$smarty.const.ENGINESKINURL}css/animate.css" media="screen">
<!-- other stylesheets -->

{* Smoothstate: smooth AJAX page transitions *}
<script defer src="{$smarty.const.ENGINEURL}js/jquery.smoothState.js"></script>
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>

<script>var ENGINEURL="{$smarty.const.ENGINEURL}";</script>
<script src="{$smarty.const.ENGINEURL}js/bbsengine6.js"></script>
<!-- other scripts -->
{/block}
</head>
<body id="body" class="scene element fadeIn">
  {include file="pageheader.tmpl"}
  {include file="topbar.tmpl" data=$data|default:NULL}
  {block name="content"}
    <!-- page content -->
  {/block}
  {include file="pagefooter.tmpl"}
</body>
</html>
```

**Key Requirements:**
1. jQuery must load before smoothState plugin
2. smoothState plugin must load before initsmoothstate.js
3. Use `defer` attribute for proper script loading order
4. Body element must have `id="body"` and `class="scene element fadeIn"`
5. Head element must have `id="head"`

### When to Create a Local page.tmpl

**Create a local page.tmpl ONLY if:**
- Your site needs custom page layout (different header/footer structure)
- Your site needs custom CSS framework or styling approach
- Your site has unique JavaScript requirements incompatible with shared template
- You cannot achieve your goal with Smarty `{block}` overrides

**Examples of sites with legitimate local customizations:**
- `/asimov/www/skin/tmpl/page.tmpl` - Custom layout and styling
- `/achilles/www/skin/tmpl/page.tmpl` - Custom layout and styling
- `/empyre/www/skin/tmpl/page.tmpl` - Custom layout and styling
- `/rgs/www/skin/tmpl/page.tmpl` - Custom layout and styling

**Sites should inherit from zoid6:**
All local page.tmpl files should be based on `/zoid6/shared/skin/tmpl/page.tmpl` to ensure smoothstate functionality.

## Browser Support

Smoothstate requires HTML5 History API (`pushState`):
- ✅ Chrome 18+
- ✅ Firefox 4+
- ✅ Safari 5.1+
- ✅ Edge (all versions)
- ⚠️ IE 10+ (requires polyfill for full support)

If History API is not available, smoothstate gracefully degrades and navigation works normally.

## Troubleshooting

### Smoothstate Not Working

**Check:**
1. Browser console for errors (enable `debug: true` in SmoothStateConfig)
2. jQuery is loaded before smoothState plugin
3. Body has `id="body"` attribute
4. `animate.css` is loaded
5. Page has no JavaScript errors

**Debug:**
Enable debug mode in page.tmpl:
```html
<script>
  window.SmoothStateConfig = {
    debug: true
  };
</script>
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>
```

Then check browser console (`F12 > Console`) for smoothState debug messages.

### Navigation Too Fast / Too Slow

Adjust the transition duration in page.tmpl:
```html
<script>
  window.SmoothStateConfig = {
    onStart: {
      duration: 500  // Slower (default: 250ms)
    }
  };
</script>
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>
```

### Prefetch Using Too Much Bandwidth

Disable prefetch in page.tmpl:
```html
<script>
  window.SmoothStateConfig = {
    prefetch: false
  };
</script>
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>
```

### Cache Issues

If pages seem to show stale content, reduce cache in page.tmpl:
```html
<script>
  window.SmoothStateConfig = {
    cacheLength: 1  // Cache only current page
  };
</script>
<script defer src="{$smarty.const.ENGINEURL}js/initsmoothstate.js"></script>
```

## Advanced Customization

### Custom Exit Animation

Edit the `onStart` callback in `bbsengine6/js/initsmoothstate.js`:

```javascript
onStart: {
  duration: 250,
  render: function () {
    content.toggleAnimationClass("is-exiting");
    // Add custom animation logic here
    console.log("Custom exit animation running");
  }
}
```

### Custom Entry Animation

Add an `onReady` callback:

```javascript
onReady: {
  duration: 250,
  render: function () {
    // Add custom entry logic here
    content.addClass('is-entering');
  }
}
```

### Custom Target Selectors

Change which elements get replaced:

```javascript
// Default: #head, #body
var content = $('#head, #body').smoothState(config);

// Custom: replace entire #app container
var content = $('#app').smoothState(config);
```

## Performance Notes

### Benefits
- **Perceived speed:** Page feels faster due to instant visual feedback
- **Reduced bandwidth:** Prefetch can warm cache
- **Smoother UX:** No white flashes between pages

### Costs
- **Prefetch overhead:** Pre-loads pages on hover (can use extra bandwidth)
- **Cache memory:** Stores 2 pages in memory by default
- **JavaScript size:** Adds ~27KB (minified plugin)

### Optimization Tips
1. Set `cacheLength: 1` for low-memory devices
2. Disable `prefetch: false` on slow connections
3. Use `debug: false` in production (reduces console spam)

## Related Files

**Core Files:**
- **Plugin Source:** `/bbsengine6/js/jquery.smoothState.js` (jQuery plugin, 801 lines)
- **Initialization Script:** `/bbsengine6/js/initsmoothstate.js` ⭐ (19 lines, recommended, production-tested)
- **CSS Animations:** `/bbsengine6/skin/scss/animate.scss` (animation classes)

**Base Templates (Inheritance Chain):**
- `/zoid6/shared/skin/tmpl/page.tmpl` ← Primary shared base
- `/bbsengine6/www/org/skin/tmpl/page.tmpl` ← Alternative base

**Site Implementations with Local Modifications:**
- `/asimov/www/skin/tmpl/page.tmpl`
- `/achilles/www/skin/tmpl/page.tmpl`
- `/empyre/www/skin/tmpl/page.tmpl`
- `/rgs/www/skin/tmpl/page.tmpl`

**External Documentation:**
- **Plugin Docs:** https://github.com/miguel-perez/smoothState.js
- **This Handbook:** `/bbsengine6/handbook/SMOOTHSTATE.md`

## Inheritance Chain

The template inheritance path is:

```
zoid6/shared (Base page.tmpl template)
    ↓
Individual Sites (Local page.tmpl with customizations)
    ├── asimov
    ├── achilles
    ├── empyre
    └── rgs

bbsengine6 (Plugin & JS files - used by all)
```

## Rollout Status

| Component | Status | Notes |
|-----------|--------|-------|
| bbsengine6 (Plugin & JS) | ✅ Ready | Provides plugin and initialization script |
| zoid6/shared (Base template) | ✅ Ready | Base `page.tmpl` for inheritance |
| asimov | ✅ Working | Local `page.tmpl` with customizations |
| achilles | ✅ Working | Local `page.tmpl` with customizations |
| empyre | ✅ Working | Local `page.tmpl` with customizations |
| rgs | ✅ Working | Local `page.tmpl` with customizations |
