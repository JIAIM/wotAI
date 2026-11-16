# WoT Spawn Advisor

![tests](https://github.com/JIAIM/wotAI/actions/workflows/tests.yml/badge.svg)

An in-game mod for **World of Tanks** that marks the **top-3 starting positions** on the minimap at the start of a battle: where to be ~90 seconds in, for the current map and spawn side. The advice is learned from ~4,000 parsed battle replays.

Built by hand as a learning / portfolio project: from a binary replay parser to evaluation and a working client mod.

```
replays (.wotreplay) ──► parser ──► dataset ──► features ──► zone scores ──► top-3 per map/side ──► .wotmod
                                                     │
                                                     └──► notebooks: baseline, model, class/role experiments
```

## Result in one paragraph

Players who, at 90 s, stand in one of the three advised zones deal on average **×1.33–1.38 more damage relative to their own team** than allies elsewhere (590 held-out battles). Three attempts to personalise the advice — by team composition (gradient boosting), by tank class and by tank role — **did not beat the single per-map heatmap**. Good zones on a map are the same for everyone; how to play there (front line vs second line) is up to the tank.

## How it works

### 1. Replay parser (`src/spawn_advisor/replay/`)
Written from scratch, no third-party replay libraries.

- **Container**: magic `0x11343212`, JSON blocks (battle header and results), then an encrypted packet stream.
- **Crypto**: Blowfish-ECB with the public replay key; each 8-byte block is XOR-ed with the previous plaintext block; then zlib.
- **Packets**: `[size u32][type u32][time f32][payload]`. Types used: map name (15), roster (50), entity positions (10), battle period changes (8).
- **Battle start** is found *by content* (a pickled period tuple `(3, …)`), because the method id differs between client versions. Pickles are read with a `SafeUnpickler` that refuses any class.
- Works on clients 2.0–2.4.1. Results are cached per parser version.

### 2. Dataset and features (`dataset.py`, `features.py`, `tankopedia.py`, `roles.py`)
- One row per ally tank: position at 90 s, survived to 90 s, damage, assist, spotting, win.
- Tank class and tier from the WG Tankopedia API; tank **roles** (assault/sniper/support TD, break-through HT, …) parsed from the client's packed BigWorld XML in `scripts.pkg`.
- Target: `damage_rel` = tank damage / mean damage in its battle (computed before filtering).
- Filters: random battles in standard mode (`ctf`), no bots, alive at 90 s, client 2.x.
- Final table: **57,959 rows, 4,075 battles**; advice covers 45 maps. Each map is split into 100×100 m zones.

### 3. Recommendation (`recommend.py`)
Smoothed heatmap per (map, side, zone):

```
score = (Σ damage_rel + K·1.0) / (n + K),   K = 50,  zones with n ≥ 10 only
```

Then a greedy pick of the 3 best zones at least 200 m apart.

### 4. Delivery
- **`mod/`** — the client mod (Python 2.7). Hooks the minimap component and draws coloured vector rings (purple/turquoise/green = rank 1/2/3) using the same minimap entry the game uses for view-range circles. F9 toggles. Hidden for artillery.
- **`live.py`** — an earlier external version: watches `temp.wotreplay`, detects map and side from the first packets (152/152 correct), and shows a plot.

## Evaluation

**Split by battle**, never by row: all allies of a battle are either in train or in test. A frozen list of 3,485 "dev" battles is used for all tuning with 5-fold CV; **590 newer battles** were held out and checked once per experiment.

**Metric — lift**: mean `damage_rel` of tanks that *were* in an advised zone at 90 s, divided by the mean of tanks that were not. MAE was tried first but picked parameters that hurt the product; lift measures the product directly.

| Experiment | CV lift (dev, 5 folds) | Held-out lift (590 battles) | Notebook |
|---|---|---|---|
| Smoothed heatmap, top-3 | **1.325 ± 0.018** | **1.384** | 02 |
| Separate heatmap per class | 1.214 ± 0.027 | — | 02 |
| HistGradientBoosting (class, tier, team composition, zone prior) | 1.296 ± 0.020 | 1.342 | 03 |
| Product version (top-3 with 200 m spread) | 1.289 ± 0.016 | 1.332 | 04 |
| Per-class, shrunk to the map heatmap (K = 50) | 1.289 ± 0.016 | 1.342 | 04 |
| Per-role, shrunk to the map heatmap (K = 50) | 1.285 ± 0.016 | 1.311 | 05 |

Differences between the last three rows are within fold-to-fold noise; no shrinkage strength (K from 0 to 200) gave a gain larger than that noise.

Other findings:
- Team class composition is mirrored between the two teams in **96.7%** of battles, so "enemy composition" adds nothing.
- Per-role lift of the shared advice is positive for every role, e.g. support TDs (FV4005-like) **1.36**, sniper TDs 1.27, break-through HTs 1.25.
- **Artillery: lift ≈ 0.98** — the advice does not help, so the mod hides it for SPGs.
- Light tanks: if their contribution is measured as damage + damage on spotting, the shared advice gives them nothing (0.98), while zones chosen by that metric give 1.21 ± 0.06. Not shipped: choosing what matters for LTs is a product decision, not a data result.

## Limitations

- **Association, not causation.** Stronger players may simply choose these zones. A within-player comparison or a skill adjustment is the next step.
- **Biased sample.** ~77% of battles in the data are wins: shared and recorded replays skew toward good games and good players.
- **Coarse.** 100 m zones and a single 90 s snapshot cannot tell "front line" from "second line" in the same area.
- Encounter/assault modes, Epic battles and maps with little data are not covered.

## Data

Raw replays are **not** in this repository: they contain other players' nicknames.

| Source | Replays |
|---|---|
| Own and friends' replays | 1,370 |
| wot-record.com | 3,898 |

The wot-record.com replays were downloaded by a script (`download_replays*.py`) that iterates over replay ids. The site's `robots.txt` disallows automated access to `/download/`, and no permission was obtained from the site owner. Anyone reproducing this work should ask the site owner first or use their own replays.

## Run it

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q

# full rebuild: replays in data/raw/<source>/ → dataset → features → advice → mod
python -m spawn_advisor.release                  # needs Python 2.7 as `py -2.7` for the mod
python -m spawn_advisor.release --skip-dataset   # reuse parsed data
python -m spawn_advisor.roles "<WoT>\res\packages\scripts.pkg"   # tank roles for notebook 05
```

Tankopedia needs a free WG API application id in `.env` as `WG_APPLICATION_ID=...`.

**Install the mod:** copy `dist/spawn_advisor_<version>.wotmod` to `World_of_Tanks\mods\<game version>\`. Settings (colours, ring sizes, toggle key, show for artillery) are constants at the top of `mod/mod_spawn_advisor.py`.

## Repository layout

```
src/spawn_advisor/replay/   parser: container, crypto, packets, positions, battle start
src/spawn_advisor/          dataset, features, tankopedia, roles, recommend, live, release
mod/                        client mod + build script (.py → Python 2.7 .pyc → .wotmod)
notebooks/                  01 EDA · 02 baseline · 03 model · 04 class advice · 05 roles
tests/                      pytest, with small replay fixtures
```

## Possible next steps

1. Control for player skill (within-player comparison) to test whether the advice *causes* more damage.
2. "Overloaded flank": does a zone stay good when many allies already went there? This would be the first battle-dependent advice.
3. Finer zones (50 m or kernel density) to separate front and second lines.
