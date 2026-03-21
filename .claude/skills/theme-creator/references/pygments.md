# Pygments CSS

Pygments renders code blocks server-side — HTML comes pre-highlighted with no client-side JavaScript. Supports 500+ languages.

## Generate CSS

```bash
pygmentize -S <style> -f html > themes/{name}/static/pygments.css
```

## Common Styles

`monokai`, `dracula`, `github-dark`, `one-dark`, `gruvbox-dark`, `nord`

Theme CSS controls the colors.
