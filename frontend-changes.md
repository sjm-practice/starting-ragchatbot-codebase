# Frontend Code Quality Changes

## Summary

Added Prettier-based code formatting and ESLint linting to the frontend development workflow.

## Files Added

### `frontend/package.json`
- Defines the frontend as an npm project (`ragchatbot-frontend`)
- Dev dependencies: `prettier@^3.3.3`, `eslint@^9.9.0`
- npm scripts:
  - `npm run format` — auto-format all JS/HTML/CSS with Prettier
  - `npm run format:check` — check formatting without modifying files
  - `npm run lint` — lint `script.js` with ESLint
  - `npm run quality` — run both format check and lint (CI-friendly)

### `frontend/.prettierrc`
Prettier configuration:
- Single quotes in JS
- Semicolons on
- 2-space indentation
- 100-character print width
- ES5 trailing commas
- LF line endings

### `frontend/.eslintrc.json`
ESLint configuration for browser JS:
- Target: browser environment, ES2021
- `marked` declared as a read-only global (loaded via CDN)
- Rules: `no-unused-vars` (warn), `eqeqeq` (error), `no-var` (error), `prefer-const` (warn)

### `check-frontend.sh` (project root)
Shell script to run all frontend quality checks:
- `./check-frontend.sh` — checks formatting + lints (exits non-zero on failure)
- `./check-frontend.sh --fix` — auto-formats all files with Prettier
- Auto-installs npm deps if `node_modules` is missing

## Files Modified

### `frontend/script.js`
Applied consistent Prettier formatting throughout:
- Changed 4-space indentation to 2-space (matching Prettier config)
- Removed extra blank lines (e.g. between `setupEventListeners` sections)
- Added trailing commas to multi-line object/array literals
- Normalized arrow function parentheses: `forEach(button =>` → `forEach((button) =>`
- Consistent template literal indentation in `createLoadingMessage` and `addMessage`
- Wrapped long `addMessage` call in `createNewSession` across multiple lines for readability

No logic was changed — only formatting.

---

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
