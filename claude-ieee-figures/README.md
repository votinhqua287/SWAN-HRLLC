# claude-ieee-figures

A private Claude Code plugin marketplace for IEEE paper tooling.

It currently ships one plugin, **`ieee-figures`**: the `ieeefig` matplotlib
module plus a skill that makes Claude use it correctly, so figures across every
paper come out with the same geometry, the same encoding, and an export that
IEEE PDF eXpress accepts.

## Install

```bash
claude plugin marketplace add <your-github-user>/claude-ieee-figures
```

```bash
claude plugin install ieee-figures@ieee-paper-tools
```

For a private repository, authenticate first with `gh auth login` (or have an
SSH key with access); Claude Code uses the machine's existing git credentials to
fetch the marketplace.

Confirm it loaded:

```bash
claude plugin details ieee-figures
```

The `Component inventory` section reads `Skills (1)  ieee-figures`.

## What the plugin enforces

| Rule | Mechanism |
|---|---|
| No error bars, caps, shaded bands, or smoothing on a simulation-result figure | `make_trend` refuses `show_shadow=True`; `assert_house_style` rejects any `fill_between` or errorbar artist |
| `xlim` exactly the first and last swept value | `make_trend`, re-checked by `assert_house_style` |
| `xticks` exactly the swept values and nothing else | `FixedLocator(x)`, re-checked by `assert_house_style` |
| End markers sit on the axis frame | `clip_on=False` on every series |
| IEEE column geometry | `IEEE_SINGLE = 3.5`, `IEEE_DOUBLE = 7.16`, base font 8 pt, `axes.linewidth` 0.8 |
| Readable in grayscale and under color blindness | Okabe-Ito palette, one distinct marker and line style per series, hatch channel on bars |
| Accepted by IEEE PDF eXpress | `pdf.fonttype = 42`; Type-3 fonts are rejected by the submission system |
| Vector output only | `finalize_figure` defaults to PDF alone at 600 dpi |

## Layout

```text
claude-ieee-figures/
├── .claude-plugin/
│   └── marketplace.json          # marketplace "ieee-paper-tools"
└── plugins/
    └── ieee-figures/
        ├── .claude-plugin/
        │   └── plugin.json
        ├── skills/
        │   └── ieee-figures/
        │       ├── SKILL.md
        │       └── references/
        │           ├── api.md
        │           └── recipes.md
        └── ieeefig/
            ├── ieeefig.py
            ├── smoke_test.py
            └── README.md
```

## Develop

Work on the marketplace locally before pushing:

```bash
claude plugin validate ./
```

```bash
claude plugin marketplace add ./
```

Installed from a local directory, Claude Code reads the files in place, so edits
take effect at the next session start or after `/reload-plugins`.

Test the module:

```bash
python plugins/ieee-figures/ieeefig/smoke_test.py
```

12 checks: every helper renders and exports, and every audit branch fires on a
figure that violates it.

## Adding a second plugin

Add a directory under `plugins/` and a second object to the `plugins` array in
`.claude-plugin/marketplace.json`. The entry `name` must match the `name` in
that plugin's `plugin.json`, or installing by the manifest name fails.

## Attribution

The API shape implemented by `ieeefig` follows the specification published in
the `scientific-figure-making` skill of
[ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers)
(CC BY-NC 4.0), which documents that API without shipping an implementation.
`ieeefig` is an independent implementation written to IEEE conventions, and no
code or text from that repository is redistributed here.

The palette is the Okabe-Ito colorblind-safe set (Okabe and Ito, *Color
Universal Design*, 2008).

## License

MIT — see [LICENSE](LICENSE).
