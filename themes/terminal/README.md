# Terminal Theme

A dark terminal-inspired theme for SquishMark with pixel art titles, frosted glass navigation, animated backgrounds, and a CRT glow aesthetic.

## Features

- Pixel art site title rendered via JavaScript with dual-color split and blinking cursor
- Frosted glass sticky navigation bar with backdrop blur
- 9 configurable background effects (CSS and canvas-based)
- Server-side syntax highlighting with Pygments
- Responsive layout from mobile to desktop
- Terminal-style 404 page

## Configuration

Add these settings to your content repository's `config.yml`:

```yaml
theme:
  name: terminal
  pygments_style: monokai
  background: matrix        # optional, defaults to "plain"
  nav_image: /static/user/logo.png   # optional, replaces pixel art in navbar
  hero_image: /static/user/hero.png  # optional, replaces pixel art hero on homepage
```

### Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | `"default"` | Set to `"terminal"` to use this theme |
| `pygments_style` | string | `"monokai"` | Pygments style for code block syntax highlighting |
| `background` | string | `"plain"` | Background effect (see below) |
| `nav_image` | string | `null` | Image URL to replace the pixel art logo in the navbar |
| `hero_image` | string | `null` | Image URL to replace the pixel art hero on the homepage |

## Backgrounds

The `background` option controls the full-page background effect. Some backgrounds are pure CSS, while others use a `<canvas>` element rendered by JavaScript.

| Value | Type | Description |
|-------|------|-------------|
| `plain` | -- | Solid dark background, no overlay |
| `matrix` | JS canvas | Falling green characters (Matrix rain) |
| `scanlines` | CSS | Horizontal scan lines with CRT vignette |
| `dotgrid` | CSS | Repeating green dot grid pattern |
| `circuit` | CSS | Blue grid lines with radial vignette |
| `noise` | JS canvas | Animated TV static noise |
| `hex` | JS (DOM) | Monospaced hex dump text watermark |
| `mesh` | CSS | Overlapping colored radial gradients |
| `combo` | CSS | Dot grid + scanlines + vignette combined |

## Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Background | Dark navy | `#0a0e17` |
| Card / code block background | Slightly lighter | `#0d1117` |
| Primary accent | Blue | `#3b82f6` |
| Secondary accent | Green | `#4ade80` |
| Body text | Light slate | `#e2e8f0` |
| Secondary text | Muted slate | `#94a3b8` |

## Typography

- **Body text**: [Inter](https://fonts.google.com/specimen/Inter) (400, 500, 600, 700)
- **Code and monospace**: [JetBrains Mono](https://fonts.google.com/specimen/JetBrains+Mono) (400, 500, 600, 700)

Nav links, tags, dates, code blocks, and the pixel art title all use JetBrains Mono.

## Pixel Art Title

The site title is rendered as pixel art using a built-in JavaScript font renderer (`pixel-font.js`). The renderer reads `data-pixel-*` attributes from HTML elements and draws each character on a CSS grid.

Key behaviors:

- **Dual-color split**: The title splits at a configurable character index. Characters before the split use `color1` (blue), characters after use `color2` (green).
- **Blinking cursor**: Appended after the title text. Style is either `solid` (filled block) or `outline` (border only).
- **Skew**: The navbar title uses a `-6deg` skew for an italic effect. The hero title renders upright.
- **Scaling**: The navbar pixel art is scaled down to 22% via CSS `transform: scale()` to fit the nav bar height.

### Nav vs. Homepage

On the **homepage** (`index.html`), the navbar title renders in muted gray (`#3d4555`) to avoid competing with the large hero pixel art. On **inner pages** (posts, pages, 404), the navbar title renders in full blue/green color with a glow filter.

The hero section on the homepage displays the title at full size with a CRT glow effect (layered `drop-shadow` filters in blue and green).

### Custom Images

Setting `nav_image` or `hero_image` in the theme config replaces the corresponding pixel art with a standard `<img>` element. On the homepage, the nav image also gets a muted opacity treatment to keep focus on the hero.

## Templates

| Template | Purpose |
|----------|---------|
| `base.html` | Shared layout: nav, background canvas, footer, script loading |
| `index.html` | Homepage with hero pixel art and post card grid |
| `post.html` | Single blog post with metadata, tags, notes, and back link |
| `page.html` | Static page (e.g., About) |
| `404.html` | Terminal-style "file not found" error page |

## Static Files

| File | Purpose |
|------|---------|
| `static/style.css` | All theme styles including backgrounds and responsive breakpoints |
| `static/pygments.css` | Syntax highlighting colors for code blocks |
| `static/pixel-font.js` | Pixel art text renderer (auto-initializes on `DOMContentLoaded`) |
| `static/backgrounds.js` | Canvas-based background effects (matrix, noise, hex) |
