# Frontend Changes

## Feature: Light/Dark Mode Toggle Button

### Files Modified
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

---

### `index.html`
Added a `<button id="themeToggle">` element before the closing `</body>` tag. The button contains two inline SVGs:
- **Moon icon** — visible in dark mode (default)
- **Sun icon** — visible in light mode

Both icons include `aria-hidden="true"` since the button itself carries the accessible label via `aria-label`.

---

### `style.css`

**Light mode variables** (`body.light-mode`):
Overrides the dark-mode `:root` CSS variables with light equivalents:
- `--background: #f8fafc`
- `--surface: #ffffff`
- `--surface-hover: #f1f5f9`
- `--text-primary: #0f172a`
- `--text-secondary: #64748b`
- `--border-color: #e2e8f0`
- `--assistant-message: #f1f5f9`
- Plus shadow, welcome, and focus-ring values adjusted for light context

**Smooth transitions**:
- Added `transition: background-color 0.3s ease, color 0.3s ease` to `body`
- Added the same transition (plus `border-color`) to `.sidebar`, `.chat-messages`, `.message-content`, `.stat-item`, `.suggested-item`, `#chatInput`, and related containers

**Toggle button styles** (`.theme-toggle-btn`):
- `position: fixed; top: 1rem; right: 1rem; z-index: 100` — top-right corner
- 40×40px circle with rounded border matching the app's surface/border variables
- Hover: slight rotation (`rotate(20deg)`) and surface-hover background
- Focus: 3px ring using `--focus-ring` (consistent with other interactive elements)

**Icon swap**:
- `.icon-sun { display: none }` by default; shown in `.light-mode`
- `.icon-moon { display: block }` by default; hidden in `.light-mode`

---

### `script.js`

Added `initThemeToggle()` function called inside `DOMContentLoaded`:
- Reads `localStorage.getItem('theme')` on load and applies `light-mode` class if set
- Toggles `body.light-mode` on button click
- Persists preference to `localStorage` under key `"theme"`
- Updates `aria-label` dynamically to reflect the current mode ("Switch to dark mode" / "Switch to light mode") for screen reader users
