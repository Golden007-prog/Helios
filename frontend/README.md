# Helios — Frontend

Next.js 14 (App Router, static export) + TypeScript strict + Tailwind +
shadcn-style primitives. Targets GitHub Pages.

## Quick start

```bash
cd frontend
cp .env.example .env.local       # NEXT_PUBLIC_USE_MSW=true for mock-mode demo
npm install
npm run dev
```

Open http://localhost:3000 — every fetch is intercepted by MSW, fixtures
mirror the backend seed (Maya/MeridianBank, the seven regions, the hero
JCL). Hero-feature components render `BOB:` placeholders with their spec
inline so reviewers can see exactly what's still owed to Bob.

## Static export → GitHub Pages

```bash
GITHUB_PAGES=true PAGES_BASE_PATH=/Helios npm run build
# output is `out/` — gh-pages CI workflow uploads this
```

## Layout

```
frontend/
├── src/
│   ├── app/                 # App-Router pages
│   ├── components/
│   │   ├── ui/              # primitives (button, card, dialog, toast, …)
│   │   └── layout/          # shell, top-nav, sidebar, breadcrumbs
│   ├── features/            # per-feature non-hero components
│   ├── lib/
│   │   ├── api/             # typed client + per-feature wrappers + keys
│   │   └── env.ts
│   ├── mocks/               # MSW handlers + fixtures
│   └── test/                # vitest setup
├── e2e/                     # Playwright Maya-demo path
├── .storybook/
├── public/                  # mockServiceWorker.js
├── tailwind.config.ts
├── next.config.mjs          # output: 'export'
└── package.json
```

## Hero components owned by Bob

Every hero component renders the `BobStub` placeholder. The `data-bob-stub`
attribute makes them grep-able and lets the e2e test assert the demo path
without the hero work being done.

| Feature                | File                                           |
|------------------------|------------------------------------------------|
| Region Atlas diff view | `src/app/regions/[id]/diff/page.tsx`           |
| JJSCAN+ result viewer  | `src/app/jjscan/[id]/page.tsx`                 |
| ABEND three-pane       | `src/app/abend/[id]/page.tsx`                  |
| Confidence Score gauge | `src/app/confidence/page.tsx`                  |
| Dashboard summary      | `src/app/page.tsx`                             |

When Bob lands a hero component, replace the `<BobStub>` line — keep the
page shell.

## Scripts

```
npm run dev          # Next.js dev server
npm run build        # static export to out/
npm run typecheck    # tsc --noEmit (strict)
npm run lint         # eslint
npm run test         # vitest run (jsdom + MSW)
npm run test:e2e     # playwright run
npm run storybook    # storybook dev
```
