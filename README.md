# LM-3DCD-SG: Lifelong Mapping & 3D Change Detection on Object-Level Scene Graphs

Training-free relocalization and change detection for a robot that revisits a changing indoor scene with a map from an
earlier visit. The map is an object-level 3D scene graph. On every visit the robot builds a graph of what it currently sees,
matches it to the map, recovers its pose without an initial guess, labels each object as static, moved, added, removed or
not observed, and edits the map per object.

CS7.503 Mobile Robotics (IIIT Hyderabad) course project by **Ch Shreyash** (2024121008), **Farzana S** (2024121006) and
**Prajas Wadekar** (2024121009).

**Project page: <https://prajasw.github.io/LM-3DCD-SG/>** — the site lives in [`docs/`](docs/) and is published with
GitHub Pages from the `main` branch. To rebuild it after changing the report or the figures, run
`bash scripts/build_pages.sh`.

<details>
<summary><b>Publishing the project page (one-time, needs a repo admin)</b></summary>

A repository admin has to switch GitHub Pages on once; after that every push to `main` republishes the site.

1. Open **Settings → Pages** in <https://github.com/PrajasW/LM-3DCD-SG/settings/pages>.
2. Under **Source**, choose **Deploy from a branch**.
3. Set **Branch** to `main` and **Folder** to `/docs`.
4. **Save**. The site is live a minute later at <https://prajasw.github.io/LM-3DCD-SG/>.

Optionally, set the same URL as the repository *homepage* in **Settings → General → Website** so that GitHub shows a
link to it in the sidebar.

To edit the site, change [`docs/index.html`](docs/index.html) and [`docs/assets/`](docs/assets/), then push. There is no
build step — plain HTML, CSS and a little JavaScript, with MathJax for the equations. If the report or the figures
change, run `bash scripts/build_pages.sh` first so the page serves the up-to-date PDF.

</details>

| Document | File |
|---|---|
| **Mid-submission report (Phase 1)** | [`report/main.pdf`](report/main.pdf) (LaTeX source in [`report/`](report/)) |
| Proposal and timeline | [`docs/proposal_timeline.pdf`](docs/proposal_timeline.pdf) (course LaTeX template: [`docs/proposal_timeline.tex`](docs/proposal_timeline.tex)) |
| Project page (website) | [`docs/index.html`](docs/index.html) (styles in [`docs/assets/`](docs/assets/), figures in [`docs/img/`](docs/img/)) |

**Status (Nov 2026)**

| Phase | Due | Scope | Status |
|---|---|---|---|
| Phase 1 | mid-submission, Oct 26 | data loading, graph construction, Steps 1–3, two-visit relocalization, baselines | ✅ done (full validation split, Nov 4) |
| Phase 2 | final, Nov 23 | Steps 4–6, multi-visit setting, predicted segments | planned |
| Demo | Nov 26 | relocalization, change detection and map editing on 3RScan rooms | planned |

![pipeline](docs/img/pipeline.png)

---

## Method (Phase 1)

**Graph construction.**
- Inputs per scan: the annotated instance segments and semantic labels from 3RScan, and the 3DSSG relations.
- Floor, wall and ceiling segments become structural nodes. Every other segment with at least 50 points becomes an object node, which stores its points, centroid $\mathbf c$, class, height above the fitted floor plane $h$, and change history.
- Object extents $\mathbf e$ do not depend on the robot's pose:
  - the vertical extent is measured along the floor normal;
  - the two horizontal extents come from the minimum-area bounding rectangle of the object's footprint. PCA axes are unstable for square footprints.
- Edges are 3DSSG relations plus proximity edges.

**Step 1: candidate matches.** Objects of the same class are compared with

$$\kappa(a,b)=\sum_{k=1}^{3}\bigl|\log(e_{a,k}+\epsilon)-\log(e_{b,k}+\epsilon)\bigr|+\frac{|h_a-h_b|}{\sigma_h}.$$

Each object keeps its $k=3$ cheapest counterparts, in both directions. Identical objects therefore get several candidates, and the choice between them is left to geometry in Step 2.

**Step 2: largest consistent set.** Two candidate matches $(a,b)$ and $(a',b')$ are compatible when three conditions hold:
- they are one-to-one;
- the distance between the two objects is the same in both visits;
- the height difference between the two objects is the same in both visits.

Each test uses the tolerance $\tau=\varepsilon+\beta(r+r')$, where the $r$ terms are the object radii, because the centroid of a partly seen large object shifts. The maximum clique of the compatibility graph is the **static set** $S$. Re-solving on the remaining candidates gives further cliques, which are candidate groups of objects that **moved together** (input to Step 4).

**Step 3: pose.**
1. Solve a weighted Kabsch/Umeyama alignment on the centroids of $S$, with the two floor normals added as an extra direction pair. The normal term is weighted by the weighted variance of the visit centroids, so it counts as much as their spread.
2. Refine with point-to-plane ICP on the points of $S$ and the floor, walls and ceiling.
3. Return failure ($\bot$) instead of a pose if $|S|<3$, the centroids are collinear, or the ICP fitness is below 0.3.

All parameters are in [`configs/default.yaml`](configs/default.yaml). They were chosen only on 6 **train** rooms ([`configs/dev.yaml`](configs/dev.yaml)), never on the validation pairs.

The height test rejects matches that only fit with the scene upside down. It does **not** reject a reflection through a vertical plane, which keeps every distance and height difference; nothing in Steps 1–3 checks for that case yet.

<p align="center"><img src="docs/img/scene_graphs.png" width="80%"></p>

## Evaluation protocol

Every method sees exactly the same input:
- **Pairs.** A 3RScan reference scan is the map and one of its rescans is the new visit. Phase 1 uses the annotated segments.
- **Random transform.** Each pair has one stored random rigid transform: a uniform rotation on SO(3) and a translation drawn from U(−2, 2)³ m. It is applied to the rescan before any method sees it ([`data/pairs_val_full.json`](data/pairs_val_full.json); the earlier 17-pair subset is [`data/pairs_val.json`](data/pairs_val.json)).
- **Ground truth.** $\mathbf T^\star = \mathbf T_{\text{rescan}\to\text{ref}}\,\mathbf T_\text{rand}^{-1}$, using the transform from `3RScan.json`, which is stored column-major. It is used only for scoring.
- **Metrics:**
  - success at the RIO thresholds, 10 cm / 10° and 20 cm / 20°;
  - registration recall (RMSE of the visit's points below 0.2 m, as in SGAligner, SG-PGM and SG-Reg);
  - median rotation (RRE) and translation (RTE) error;
  - time per pair.
- **Failures.** A pair on which a method declines to return a pose counts as a failure.
- **Aligned run.** A second run gives the rescan already aligned to the reference. This is the setting the learned baselines were trained and evaluated in, and it also checks that their adapters work.

## Results (Phase 1, full validation split: 47 rooms, 110 pairs)

"Wrong" = a pose was returned but is outside 20 cm / 20°. Times are per pair for the pose; our graph construction adds 0.11 s.

| Method | Pose returned | Wrong | succ. 10cm/10° | succ. 20cm/20° | RR@0.2m | median RRE | median RTE | time/pair | succ. 20/20, pre-aligned |
|---|---|---|---|---|---|---|---|---|---|
| SGAligner (ICCV'23) | 40.9% | 9.1% | 27.3% | 31.8% | 32.7% | 1.45° | 5.4 cm | 3.37 s | 79.1% |
| SG-PGM (CVPR'24) | 100% | 66.4% | 27.3% | 33.6% | 35.5% | 17.9° | 68.3 cm | 4.09 s | 74.5% |
| FPFH + TEASER++ | 100% | 9.1% | 75.5% | 90.9% | 93.6% | 0.98° | 3.8 cm | 1.82 s | 90.9% |
| FPFH + RANSAC | 100% | 6.4% | **78.2%** | **93.6%** | **96.4%** | **0.96°** | **3.7 cm** | 4.83 s | 92.7% |
| Ours, centroid pose only | 96.4% | 11.8% | 59.1% | 84.5% | 89.1% | 1.63° | 7.2 cm | <0.01 s | 83.6% |
| **Ours (Steps 1–3)** | 93.6% | **4.5%** | 72.7% | 89.1% | 91.8% | 0.97° | 4.0 cm | **0.13 s** | 89.1% |

<p align="center"><img src="docs/img/success_curves.png" width="62%"> <img src="docs/img/runtime.png" width="34%"></p>

**Invariance.**
- At 20 cm / 20° and in RR our accuracy is the same with and without the random transform.
- At 10 cm / 10° it drops from 78.2% to 72.7%. Translation error is measured at the frame origin, which the transform moves metres away from the scene, so a sub-degree rotation error adds centimetres.
- The learned scene-graph aligners collapse under the transform: SGAligner drops from 79% to 32%, and SG-PGM from 75% to 34%.
- Their node encoders take object points in world coordinates. SG-PGM's own random-transform evaluation rotated only the registration points, never the scene-graph objects.

**Accuracy and cost.**
- Ours is within the 95% intervals of both FPFH methods (Wilson: ours 82–94%, RANSAC 87–97%). RANSAC succeeds on 5 pairs we fail, and we succeed on none it fails (McNemar p = 0.06).
- Ours returns the fewest wrong poses: 5, against 7–73 for the baselines. 7 of our 12 failures are declines.
- Steps 1–2 take 2.6 ms on 3–120 candidates, ICP 0.13 s and graph construction 0.11 s: about 20× less than RANSAC, on annotated segments.
- Ours also returns object correspondences and the static set (precision 72.6%, recall 65.6% against unchanged instances), which the change-detection steps need. Many of the "errors" are objects annotated as moved that shifted only a few centimetres.

**Failure modes** (all 12 are listed in the report's appendix).
- **Repeated layouts:** a café with a row of identical table, chair and menu sets and no walls. One rescan is matched one set off and another is flipped 180° about the vertical; both pass the ICP fitness gate, which the floor dominates.
- **Near-misses:** three pairs with rotation error ≈ 4° and translation error 22–34 cm.
- **Declines:** 2 too few static objects, 2 degenerate static sets, 3 low ICP fitness. FPFH+RANSAC solves 5 of these 7 from walls and floor, which motivates a structure-only fallback.

| | |
|---|---|
| ![consistency](docs/img/consistency.png) | ![relocalization](docs/img/relocalization.png) |
| Distance test on all candidate pairs of the 110 pairs: it keeps 90.9% of pairs between correct, unchanged matches and 23.3% of the rest. The maximum clique removes most of the remainder. | One pair after relocalization (RTE 3.3 cm): the static clique (blue), and the remaining consistent groups (orange), which are candidates for Step 4. |

Raw results: [`results/full_val/`](results/full_val/), with one JSON line per pair and method, plus `per_pair*.csv`, `two_visit_table*.md` and the run logs. The first 17-pair subset (4 rooms) is kept in [`results/`](results/); its per-pair outcomes are in [`docs/img/per_pair.png`](docs/img/per_pair.png).

## Baselines

| Method | How it is run here |
|---|---|
| **SG-PGM** (CVPR'24), strongest scene-graph aligner with public 3RScan weights | released checkpoint and the repo's own model, dataset class and collate function ([`baselines/adapters/run_sgpgm.py`](baselines/adapters/run_sgpgm.py)) |
| **SGAligner** (ICCV'23) | released checkpoint with K=2 node matches, GeoTransformer (3DMatch) and GC-RANSAC ([`baselines/adapters/run_sgaligner.py`](baselines/adapters/run_sgaligner.py)) |
| **FPFH + RANSAC** | Open3D: 5 cm voxels, mutual filter, then point-to-plane ICP ([`scripts/run_classical.py`](scripts/run_classical.py)) |
| **FPFH + TEASER++** | TEASER++ (GNC-TLS, max clique) on mutual nearest-neighbour FPFH matches, then ICP |
| SG-Reg (T-RO'25), SGAligner++ (2025) | cited only: SG-Reg releases only a ScanNet-trained model and a C++ back-end; SGAligner++ has no code |

Both learned checkpoints were trained on the 3RScan **train** split, and all evaluation rooms come from **val**.

**Adapter.** [`export_scan3r.py`](baselines/adapters/export_scan3r.py) writes our pairs, including the stored random transforms, into SGAligner's full-scan data layout. SGAligner's own unmodified preprocessing then builds the per-scan pickles (attribute vocabulary 164, relations 41, matching the checkpoints). SG-PGM reads the same files.

**Fairness fixes** (each one helps the baselines):
- **SGAligner's RANSAC.** GC-RANSAC's PROSAC sampler requires correspondences sorted by score. With pip `pygcransac==0.1.1`, unsorted input returns no model even on synthetic data with 50% inliers. [`baselines/patches/sgaligner.patch`](baselines/patches/sgaligner.patch) sorts by GeoTransformer score and retries with the uniform sampler. The same patch replaces the hard-coded dataset path with `$SCAN3R_ORIG_DIR`.
- **Normal orientation for FPFH.** Normals are oriented towards the scan centre. Open3D's default sign depends on the frame, and without the fix FPFH+TEASER++ dropped from 82% to 41% under the random transform.
- **3DSSG `inside` relations** are removed before SGAligner preprocessing, which rejects them.

## Repository layout

```
lifelong/                  the method
  data.py                  3RScan metadata/scans, 3DSSG objects & relationships
  graph.py                 scene-graph construction (pose-invariant extents, floor plane, edges)
  candidates.py            Step 1
  consistency.py           Step 2 (compatibility matrix, maximum clique, further consistent groups)
  pose.py, relocalize.py   Step 3 and the end-to-end call
  protocol.py, metrics.py, transforms.py, config.py
configs/                   default.yaml (all thresholds), dev.yaml (train rooms used for tuning), full_val.yaml
scripts/
  download_subset.py       N validation rooms from a 3RScan mirror (labels + semseg + segs only)
  make_pairs.py            pairs + stored random SE(3) (--aligned: pre-aligned sanity setting)
  run_ours.py              ours + centroid-only ablation       -> results/ours*.jsonl
  run_classical.py         FPFH+RANSAC, FPFH+TEASER++          -> results/fpfh_*.jsonl
  evaluate.py              one scorer for all methods          -> results/two_visit_table*.md, per_pair*.csv
  make_figures.py          every figure of the report          -> report/figures/*.pdf
  run_all.sh               tests -> pairs -> all methods -> evaluation (17-pair subset)
  run_full_val.sh          full validation split end to end (+ RGB-D sequences for Phase 2)
  run_full_val_learned.sh  SGAligner / SG-PGM only on the full split; waits until CUDA works
  download_sequences.py    RGB-D sequences (sequence.zip) for Step 5
  build_pages.sh           refresh the project page in docs/ from the report and the figures
baselines/
  setup_baselines.sh       fetch pinned upstream commits, apply patch, build extensions, download weights
  patches/                 sgaligner.patch
  adapters/                export_scan3r.py, prepare_baselines.sh, run_sgaligner.py, run_sgpgm.py, configs/
  requirements_sgbase.txt  exact package versions of the baseline environment
tests/test_pipeline.py     synthetic rooms: Kabsch, pose invariance, duplicates, moved group, declining
report/                    mid-submission report: main.tex (course template, 11pt), references.bib, figures/, main.pdf
docs/                      project page (GitHub Pages): index.html, assets/, img/, paper/
                           proposal (PDF + LaTeX template + references.bib), study guide, README images
```

## Setup

**1. Our method and the classical baselines** (env `mrproj`):

```bash
conda env create -f environment.yml          # python 3.10, open3d 0.18, python-igraph, eigen 3.4, ...
conda activate mrproj
pytest -q tests                              # 8 synthetic tests
```

**2. Data.** Downloading 3RScan requires its [Terms of Use](https://github.com/WaldJohannaU/3RScan); the official route is the ToU form, which gives you a `download.py` script. Put the files in this layout:

```
data/meta/   3RScan.json, train_scans.txt, val_scans.txt         (campar.in.tum.de/public_datasets/3RScan/)
             objects.json, relationships.json                     (campar.in.tum.de/public_datasets/3DSSG/3DSSG/)
data/3RScan/<scan_id>/labels.instances.annotated.v2.ply, semseg.v2.json, mesh.refined.0.010000.segs.v2.json
```

[`scripts/download_subset.py`](scripts/download_subset.py) fetches N validation rooms (reference + rescans) from the Hugging Face dataset mirror [`maartenImjalli143/3RScan`](https://huggingface.co/datasets/maartenImjalli143/3RScan). That is what was used here: `--rooms 47 --min-rescans 1` for the full split (`--rooms 4` for the first subset).

**3. Learned baselines** (env `sgbase`):
- Python 3.11 with torch 2.7.1+cu128 (tested on an RTX 2080 Ti, sm_75).
- Exact versions are in [`baselines/requirements_sgbase.txt`](baselines/requirements_sgbase.txt). In particular pin `torch_geometric==2.5.3`, because newer versions route `knn_graph` to pyg-lib.

```bash
conda create -n sgbase python=3.11 && conda activate sgbase
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
pip install torch_geometric==2.5.3 \
  https://data.pyg.org/whl/torch-2.7.0%2Bcu128/torch_cluster-1.6.3%2Bpt27cu128-cp311-cp311-linux_x86_64.whl \
  open3d==0.18.0 numpy==1.26.4 pygcransac plyfile scipy yacs easydict einops coloredlogs tqdm pyyaml ipdb \
  scikit-learn tensorboard tensorboardX trimesh torchsummary addict pyquaternion opencv-python-headless gdown
CUDA_HOME=/usr/local/cuda bash baselines/setup_baselines.sh   # SGAligner, SG-PGM, TEASER++ + weights
```

## Reproducing the results and the report

```bash
tmux new -d -s fullval 'bash scripts/run_full_val.sh'   # full split, ~2 h (GPU for SGAligner / SG-PGM)
python scripts/make_figures.py --config configs/full_val.yaml --results results/full_val   # report/figures/*.pdf
cd report && tectonic -X compile main.tex     # or: latexmk -pdf main.tex
```

The thresholds were tuned on the dev rooms with:

```bash
python scripts/make_pairs.py --config configs/dev.yaml
python scripts/run_ours.py --config configs/dev.yaml --out-dir results/dev
python scripts/evaluate.py --config configs/dev.yaml --results results/dev
```

On dev, ours gets 86.4% with no wrong poses, and both FPFH baselines get 95.5%.

**GPU note.** Only SGAligner and SG-PGM use the GPU. If they fail at start-up with `CUDA unknown error`, check `python -c "import ctypes; print(ctypes.CDLL('libcuda.so.1').cuInit(0))"`. A result of 999 means the node's driver is broken (on gnode090, `/dev/nvidia-uvm` returned an I/O error). Run `scripts/run_full_val_learned.sh` on another node. `/scratch` is local to each node, so copy `/scratch/$USER/3RScan_seq` across if Step 5 needs it.

## Models and artefacts

No models were trained in this project, so there are no Hugging Face or WandB model artefacts. The only Hugging Face resource used is the 3RScan dataset mirror [`maartenImjalli143/3RScan`](https://huggingface.co/datasets/maartenImjalli143/3RScan). The baseline checkpoints are the authors' releases:

| Checkpoint | Source |
|---|---|
| SGAligner | [Google Drive](https://drive.google.com/drive/folders/10-JNxWLxPFQ2q6_zY-9HXIO-Qx-vhmmT) |
| SG-PGM | [Google Drive](https://drive.google.com/drive/folders/1E60DFV7uTdvwgIxf6_eTIbayQH7uYZzP) |
| GeoTransformer (3DMatch) | [GitHub release](https://github.com/qinzheng93/GeoTransformer/releases/tag/1.0.0) |

## Upstream code

| Code | Commit | Notes |
|---|---|---|
| [SGAligner](https://github.com/sayands/sgaligner) | `51cd572` | its [GeoTransformer](https://github.com/sayands/GeoTransformer) submodule at `9bba304` |
| [SG-PGM](https://github.com/dfki-av/sg-pgm) | `233d852` | unmodified |
| [TEASER++](https://github.com/MIT-SPARK/TEASER-plusplus) | `52a9c52` | |

## References

The full bibliography is in [`report/references.bib`](report/references.bib). The key works:

| Work | Venue |
|---|---|
| RIO / 3RScan (Wald et al.) | ICCV 2019 |
| 3DSSG (Wald et al.) | CVPR 2020 |
| SGAligner (Sarkar et al.) | ICCV 2023 |
| SG-PGM (Xie et al.) | CVPR 2024 |
| SG-Reg (Liu et al.) | T-RO 2025 |
| PCM (Mangelson et al.) | ICRA 2018 |
| TEASER (Yang et al.) | T-RO 2021 |
| CLIPPER (Lusk et al.) | ICRA 2021 |
| Objects Can Move (Adam et al.) | ECCV 2022 |
| Living Scenes (Zhu et al.) | CVPR 2024 |
| Khronos (Schmid et al.) | RSS 2024 |
