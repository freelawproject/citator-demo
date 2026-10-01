# Citator Demo

A static preview of the Free Law Project citator: for each opinion, how it
treats the cases it cites, how later opinions treat it, and its route
through the courts. Built with Eleventy from the citator pipeline's
output; no backend.

## Stack

- [Eleventy](https://www.11ty.dev/) renders Nunjucks templates in `src/`
  and `_includes/` to `_site/`.
- [Tailwind CSS](https://tailwindcss.com/) with CourtListener's design
  tokens (`tailwind.config.js`). Repeated patterns are component classes
  in `assets/css/styles.css`; one-off styling is inline utilities.
- [Alpine.js](https://alpinejs.dev/), the CSP build CourtListener ships
  (`@alpinejs/csp`). Templates reference component members only; all
  logic lives in `assets/js/alpine/`.
- Python 3.13 (`scripts/`) turns the data source into the JSON the
  templates read. Dependencies are managed with `uv`.

## Development

Prerequisites: Node 20+, Python 3.13+, [`uv`](https://docs.astral.sh/uv/).

```sh
npm install
uv sync --group dev

# build from the fixtures (no data-source/ needed)
CITATOR_DEMO_DATA=mock npm run build

# build from the real data in data-source/
npm run build

# serve the built site
python3 -m http.server 8080 -d _site

# tests, lint, types
npm test
npm run lint
```

`npm run build` runs three steps: `build:data` (Python, writes `_data/`),
`build:css` (Tailwind) and `build:eleventy`. Always run the full chain
after changing the stylesheet or the data: Eleventy alone copies neither.

### Build flags

| Variable | Default | Effect |
|---|---|---|
| `CITATOR_DEMO_DATA` | real | `mock` builds from `scripts/mock_data.py` instead of `data-source/`. |
| `CITATOR_DEMO_VALIDATION` | off | `1` shows the marks comparing each treatment with an expert's label, and the Validation filter on both tabs. A review aid, off in the published site. |

Flags are written to `_data/flags.json` and read by the templates as
`flags.<name>`.

## Layout

```
.eleventy.js            Eleventy config (input src/, data _data/)
_data/                  JSON written by the build (gitignored), plus
                        allOpinions.js and build.js
_includes/
  layouts/base.njk      page shell: header, footer, script tags
  macros/               reusable Nunjucks macros
    icons.njk           inline SVG icons
    treatment.njk       severity pill, validation mark
    status.njk          Disposition / On appeal / Later courts rows
    evidence.njk        evidence card (pill, rationale, quote, link)
    lists.njk           clamped citation list with "+N"
    list_header.njk     sort menu, treatment filter, column labels
  partials/             the opinion page's tabs and the Back control
src/                    pages: index, opinion, about
assets/
  css/styles.css        Tailwind input
  js/alpine/components/ one component per page or list
  js/alpine/composables/ shared Alpine behaviour (list toggle, highlight)
scripts/
  build_data.py         entry point: data source → _data/*.json
  data_source.py        the DataSource contract both data modules return
  real_data.py          reads data-source/
  mock_data.py          hand-written fixtures
  taxonomy.py           treatment labels, severities, wording
  render.py             opinion text → page html
  history.py            the History tab's graph
  courts.py             court list and court picker
  cl_html.py            CourtListener / Centralia html → structured text
  model_output.py       interpreting the citator's own output: quotes,
                        authority names, dispositions, courts in prose
  tests/                pytest suite
data-source/            input data (gitignored)
```

## Data

The site works like a citator's citation table. Each opinion's citation
groups (the cases its text cites, with how often each is mentioned and
the treatment applied) are first filtered to cases: a group with no case
name, no short name and no case reporter citation, such as a statute, a
law review article or an unattached "Id.", is not an authority
(`model_output.py`). The rest are resolved to opinions in the collection: by the
cluster id the extraction attached; else by a reporter citation the
opinion or its metadata lists; else by the first party's name, when only
one opinion in the collection has it. Every group resolved to an opinion
in the collection is one edge from the citing opinion to the cited
opinion. The Authorities tab is the edges
where an opinion is the citing side, in the active voice
("Distinguishes"); the Cited By tab, the status rows and the home cards
are the edges where it is the cited side, in the passive ("Distinguished
by"); the mention count is the same number on both. A treatment a citing
opinion only reports another court applying is the "as recognized by"
form and keeps that treatment's severity. The Cited By tab lists one row
per citing opinion, however many treatments run between the two, with
one evidence card per negative treatment. The citing-scope CSVs say
which citing opinions were fetched for each anchor; they create no rows.

Treatments roll up into five severity tiers, most serious first: Stop,
Warning, Caution, Neutral and Positive (an affirmance). The first three
are the negative tiers; only they produce evidence cards, text markers
and expert-disagreement marks (`scripts/taxonomy.py`). An opinion's own
disposition renders in the past tense as the court states it; one the
taxonomy has no label for renders as "Ordered" and opens the sentence
that disposed of the case.

`scripts/real_data.py` reads `data-source/`:

| Path | Contents |
|---|---|
| `anchor_opinions/{cluster_id}.json` | The anchor opinions. Required. |
| `authorities/`, `citing_opinions/`, `citing_opinions_round2/` | Further opinions, same payload shape. A cluster present in several folders is loaded once, with the first folder's tier (anchor, authority, citing). |
| `centralia/{cluster_id}.json` | A PDF re-read of an opinion whose source html is a text dump; used when `used` is true. |
| `citation_groups/{cluster_id}.json` | Citation extraction output: the writings' html, one group per cited case (`gid`, `n`, `name`, `cited_cluster_id`, `citations`, `cited_as`, `n_mentions`), kept and removed spans (`occurrences`), added mentions (`manual`). The group number `n` is the key the treatments use. |
| `treatments/{cluster_id}.json` | Per group: `applied`, `severity`, `direction`, `quote`, `rationale`, `recognized[]`; plus the opinion's `disposition`, `on_appeal` and expert `gold`. |
| `cited_metadata.json` | Date, status, court and citations for cited clusters. |
| `citing_counts_*.json` | How often cited opinions are cited, for pages outside the Cited By scope. |
| `citing_edges.csv`, `citing_edges_round2.csv` | The citing scope: which citing opinions were fetched for which anchor (`citing_cluster_id`, and `anchor_opinion_id` or `anchor_cluster_id`). |

An opinion payload holds `cluster_id`, `case_name`, `docket_number`,
`citations`, `court`, `court_full_name`, `court_jurisdiction`,
`date_filed` and `opinions`, one entry per writing with `id`, `type`,
`author` and `html`.

The build writes `_data/opinions/{cluster_id}.json` (one per page),
`index.json` (the home list), `scope.json` (counts for the About page),
`flags.json`, `courts.json`, `court_picker.json`, `court_categories.json`,
`court_jurisdictions.json` and `treatments.json` (the taxonomy table).

## Pages

- **Home** lists every opinion, newest first, with search by name or
  citation, a court picker, "Anchor opinions only" (on by default) and
  severity toggles for each of the three status questions (disposition,
  on appeal, later courts); ticked severities are a union. Filter state
  lives in the URL.
- **Opinion** shows the case card and status rows, then four tabs:
  Opinion (the text, every citation linked to its Authorities row, with
  a marker for a negative treatment), Authorities and Cited By (each with
  search by name or citation, a sort menu and a severity filter over the
  applied and recognized treatments, as a union) and History (the case's
  route through the courts: court levels along the bottom, time up the
  side).
- **About** explains the preview and the taxonomy; its counts come from
  `scope.json`.

## Continuous integration

`lint.yml` runs pre-commit (ruff) and mypy. `build-check.yml` runs the
Python tests and a full build from the fixtures, then checks the output.

## Deploying

The site is hosted on Netlify. The real data is not in the repository
and the data step takes several minutes, so the site is built locally
and the `_site/` folder is uploaded as-is. Netlify's own git builds are
turned off for the site; pull requests are checked by GitHub Actions
instead.

```bash
# once per machine: sign in and link this folder to the Netlify site
npx netlify-cli login
npx netlify-cli link

# publish: stop any running `npm run dev` first, then build and upload
npm run build
npx netlify-cli deploy --prod --dir=_site
```

Run both commands from the project root. The link is stored in
`.netlify/` (gitignored). Dropping `--prod` uploads a preview at a
unique URL without replacing the live site. A running dev server
rewrites `_site/` from its own cached state, so it must be stopped
before the build that gets published.

## License

BSD-2-Clause. See [LICENSE](LICENSE).
