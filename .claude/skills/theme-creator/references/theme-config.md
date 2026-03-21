# ThemeConfig Extensibility

ThemeConfig has 5 built-in fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Theme name |
| `pygments_style` | `str` | Pygments syntax highlighting style |
| `background` | `str \| None` | Background option (theme-specific) |
| `nav_image` | `str \| None` | Navigation image path |
| `hero_image` | `str \| None` | Hero section image path |

**Any extra fields** added under `theme:` in `config.yml` are accessible as `{{ theme.fieldname }}` in templates. This is enabled by `model_config = {"extra": "allow"}` on `ThemeConfig`.

## Example — Custom Accent Color

```yaml
# config.yml
theme:
  name: my-theme
  pygments_style: monokai
  accent_color: "#ff6600"
  show_sidebar: true
```

```jinja2
{# In a template #}
<style>
  :root { --accent: {{ theme.accent_color }}; }
</style>
{% if theme.show_sidebar %}
  <aside>...</aside>
{% endif %}
```
