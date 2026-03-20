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
