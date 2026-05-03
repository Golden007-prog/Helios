# Frontend — Page Map, Mock Mode, Hero Components

Companion to `frontend/README.md`. Use this when you want to understand
how the pages are organized, how mock-mode demos work, and what's left
for Bob.

---

## Page map

| Route                       | Page file                                    | Hero? |
|-----------------------------|----------------------------------------------|-------|
| `/`                         | `src/app/page.tsx`                           | partial — landing summary tile is BOB |
| `/login`                    | `src/app/login/page.tsx`                     | no    |
| `/regions`                  | `src/app/regions/page.tsx`                   | no    |
| `/regions/[id]`             | `src/app/regions/[id]/page.tsx`              | no    |
| `/regions/[id]/diff`        | `src/app/regions/[id]/diff/page.tsx`         | **yes** — diff renderer is BOB |
| `/jjscan`                   | `src/app/jjscan/page.tsx`                    | no    |
| `/jjscan/[id]`              | `src/app/jjscan/[id]/page.tsx`               | **yes** — result renderer is BOB |
| `/abend`                    | `src/app/abend/page.tsx`                     | no    |
| `/abend/[id]`               | `src/app/abend/[id]/page.tsx`                | **yes** — three-pane content is BOB |
| `/confidence`               | `src/app/confidence/page.tsx`                | **yes** — gauge is BOB |
| `/review`                   | `src/app/review/page.tsx`                    | no    |
| `/runbooks`                 | `src/app/runbooks/page.tsx`                  | no    |
| `/audit`                    | `src/app/audit/page.tsx`                     | no    |

Page-shell + nav + breadcrumbs + supporting cards are real on every
page. Hero components render `BobStub` placeholders with the spec inline
so reviewers can see exactly what's missing.

## Mock mode

Set `NEXT_PUBLIC_USE_MSW=true` (default in `.env.example`). The bootstrap
sequence:

1. `Providers` (`src/components/providers.tsx`) imports `mocks/browser`
   dynamically and starts the worker.
2. While the worker boots, the page shows `Booting mock backend…`.
3. Once live, every fetch is intercepted by `src/mocks/handlers.ts` and
   served from `src/mocks/fixtures.ts`.

Fixtures mirror `backend/migrations/seed_demo.py` — Maya, Anil, the seven
regions, and `CUST_DELETE_INACTIVE.JCL`. Hero endpoints (`/api/regions/{a}/diff/{b}`,
`/api/scan`, `/api/score`, `/api/promote`, `/api/abend`) return 501 with
`BOB:` so the UI flow is exercised end-to-end without faking the hero
result.

## Bob's frontend worklist

Each entry is one page or one component. Bob's session for that feature
should land the file marked, keeping the existing page shell and props.

| Feature                  | Bob target file                                   |
|--------------------------|---------------------------------------------------|
| Region diff renderer     | `src/app/regions/[id]/diff/page.tsx` — replace `<BobStub>` |
| JJSCAN+ result viewer    | `src/app/jjscan/[id]/page.tsx` — replace `<BobStub>` |
| ABEND syslog feedback    | `src/app/abend/[id]/page.tsx` — first `<BobStub>` |
| ABEND source view        | `src/app/abend/[id]/page.tsx` — second `<BobStub>` (Monaco) |
| ABEND analysis pane      | `src/app/abend/[id]/page.tsx` — third `<BobStub>` |
| Confidence Score gauge   | `src/app/confidence/page.tsx` — replace `<BobStub>` |
| Dashboard summary tile   | `src/app/page.tsx` — replace `<BobStub>` (uses gauge) |

To find every hero stub at once: in the browser, every placeholder has a
`data-bob-stub="true"` attribute. In the source tree:

```bash
grep -RIn 'BobStub\b\|BOB:' frontend/src
```

## Design tokens

`src/app/globals.css` defines CSS variables for `--bg`, `--fg`,
`--accent`, etc. Tailwind picks them up via the
`bg-bg`/`text-fg`/`bg-accent` classes (see `tailwind.config.ts`). Theme
toggles by setting `data-theme="light"` or `data-theme="dark"` on the
`<html>` element; `TopNav` persists the choice in `localStorage`.

## Print stylesheet

For PDF exports during the demo, every nav/sidebar element has
`data-print-hidden="true"`. Print rendering is monochrome with hidden
chrome. Add `print-page` to wrap a section that should force a page
break.

## Testing

* **Vitest + Testing Library** (`npm test`) — render tests for every
  non-hero component. Hero stubs are exercised by asserting they render
  the placeholder.
* **Playwright** (`npm run test:e2e`) — single end-to-end walking the
  Maya demo path with MSW backing. Asserts hero stubs render their
  expected placeholder text so the demo flow stays green even before
  Bob fills the heroes in.
* **Storybook** (`npm run storybook`) — primitives + a couple of
  feature components. Add a story whenever you add a primitive.

## Where to add what

| Adding…                       | Goes in                                |
|-------------------------------|----------------------------------------|
| New API endpoint wrapper      | `src/lib/api/<feature>.ts`             |
| New query key                 | `src/lib/api/keys.ts`                  |
| New MSW handler               | `src/mocks/handlers.ts` + fixtures     |
| New non-hero component        | `src/features/<feature>/`              |
| New primitive                 | `src/components/ui/`                   |
| New layout chrome             | `src/components/layout/`               |
| Constants used by both ends   | `shared/constants/`, then `make typegen` |
