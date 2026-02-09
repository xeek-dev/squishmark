# Playwright E2E Testing Skill

Use this skill when performing end-to-end browser testing with the Playwright MCP server.

## Prerequisites

The Playwright MCP server must be installed:
```bash
claude mcp add playwright -- npx @playwright/mcp@latest
```

Requires Node.js (`brew install node` on macOS).

## Available Tools

| Tool | Description |
|------|-------------|
| `mcp__playwright__browser_navigate` | Navigate to a URL |
| `mcp__playwright__browser_snapshot` | Get accessibility tree (better than screenshots for understanding page structure) |
| `mcp__playwright__browser_take_screenshot` | Capture visual screenshot |
| `mcp__playwright__browser_click` | Click an element by ref |
| `mcp__playwright__browser_type` | Type text into an input |
| `mcp__playwright__browser_fill_form` | Fill multiple form fields |
| `mcp__playwright__browser_press_key` | Press keyboard keys |
| `mcp__playwright__browser_evaluate` | Run JavaScript in the page |
| `mcp__playwright__browser_close` | Close the browser tab |
| `mcp__playwright__browser_console_messages` | Get console output |
| `mcp__playwright__browser_network_requests` | Get network requests |

## Common Workflows

### 1. Basic Page Testing

```
1. Navigate to URL
2. Take snapshot to understand page structure
3. Interact with elements using refs from snapshot
4. Take screenshot to verify visual result
```

### 2. Hard Cache Refresh

**IMPORTANT:** The following DO NOT reliably bypass the browser cache:
- `Meta+Shift+r` / `Ctrl+Shift+R` keyboard shortcuts
- `location.reload(true)` (deprecated, ignored)
- `browser_close` + `browser_navigate`
- Cache API (`caches.delete`)
- Query params on the HTML URL

**Use CDP `Network.setCacheDisabled` instead** — this is the DevTools "Disable cache" checkbox equivalent:

```
mcp__playwright__browser_run_code with code:
async (page) => {
  const client = await page.context().newCDPSession(page);
  await client.send('Network.enable');
  await client.send('Network.setCacheDisabled', { cacheDisabled: true });
  await page.reload({ waitUntil: 'networkidle' });
  await client.send('Network.setCacheDisabled', { cacheDisabled: false });
  await client.detach();
}
```

This temporarily disables cache for the reload only, then re-enables it. Works for all resource types (CSS, JS, images, fonts).

**Nuclear option** — wipe the entire browser cache:
```
mcp__playwright__browser_run_code with code:
async (page) => {
  const client = await page.context().newCDPSession(page);
  await client.send('Network.clearBrowserCache');
  await page.reload();
}
```

### 3. Verifying CSS Changes

When testing CSS changes that might be cached:

1. Verify the CSS is correct on the server:
   ```bash
   curl -s http://localhost:8000/static/theme/style.css | grep "your-selector"
   ```

2. Use the CDP cache-disable reload (see above)

3. **Always verify with computed styles**, not screenshots:
   ```
   mcp__playwright__browser_evaluate with function:
   () => getComputedStyle(document.querySelector('.your-element')).backgroundColor
   ```

### 4. Element Interaction

The snapshot returns elements with `ref` attributes. Use these refs for interaction:

```yaml
# From snapshot:
- button "Submit" [ref=e15]
- textbox "Email" [ref=e12]
```

```
# Click the button:
mcp__playwright__browser_click with ref="e15", element="Submit button"

# Type in the textbox:
mcp__playwright__browser_type with ref="e12", text="user@example.com"
```

### 5. Screenshots

```
# Viewport only
mcp__playwright__browser_take_screenshot with type="png", filename="test.png"

# Full page
mcp__playwright__browser_take_screenshot with type="png", filename="test.png", fullPage=true

# Specific element
mcp__playwright__browser_take_screenshot with type="png", filename="test.png", ref="e15", element="Submit button"
```

## Tips & Best Practices

1. **Prefer snapshots over screenshots** for understanding page structure - they show the accessibility tree which is more useful for automation

2. **Always close the browser** when done testing to free resources

3. **Start dev server in background** before testing:
   ```bash
   python scripts/start-dev.py -b              # start in background on :8000
   python scripts/start-dev.py -b --port 8001  # second instance on :8001
   python scripts/start-dev.py --name theme-test -b  # named instance
   python scripts/start-dev.py --list           # see all running servers
   python scripts/start-dev.py --stop           # stop current branch's server
   python scripts/start-dev.py --stop-all       # stop everything
   ```

4. **Clean up artifacts** after testing:
   ```bash
   rm -rf .playwright-mcp
   ```

5. **Be careful with pkill** - use specific process matching:
   ```bash
   # Good - specific
   pkill -f "uvicorn squishmark"
   lsof -ti:8000 | xargs kill

   # Bad - too broad, might kill user's browsers
   pkill -f uvicorn
   ```

6. **Wait for page load** after navigation before taking screenshots or interacting

7. **Use fullPage screenshots** when testing layouts that extend below the fold

## Troubleshooting

### "Failed to connect" on /mcp

- Ensure Node.js is installed: `node --version`
- Restart Claude Code after installing Node.js
- Check MCP status: `claude mcp list`

### Cached CSS not updating

1. Verify CSS on server with `curl`
2. Use CDP `Network.setCacheDisabled` reload (see "Hard Cache Refresh" section above)
3. Verify with `browser_evaluate` + `getComputedStyle()` — never trust screenshots alone for CSS verification

### Element not found

- Take a fresh snapshot to get current refs
- Refs change when page content changes
- Make sure element is visible (scroll if needed)
