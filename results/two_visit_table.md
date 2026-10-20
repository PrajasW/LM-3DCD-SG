# Two-visit relocalization (17 pairs)

| method        |   pairs |   returned (%) |   succ@10cm/10° (%) |   succ@20cm/20° (%) |   RR@0.2m (%) |   median RRE (°) |   median RTE (cm) |   mean time (s) | static P/R (%)   |
|:--------------|--------:|---------------:|--------------------:|--------------------:|--------------:|-----------------:|------------------:|----------------:|:-----------------|
| fpfh_ransac   |      17 |         100.00 |               76.47 |               94.12 |         94.12 |             1.07 |              3.17 |            4.82 | -                |
| fpfh_teaser   |      17 |         100.00 |               70.59 |               82.35 |         82.35 |             1.07 |              3.17 |            1.69 | -                |
| ours          |      17 |          94.12 |               70.59 |               82.35 |         82.35 |             0.99 |              3.29 |            0.13 | 60.5/58.5        |
| ours_centroid |      17 |          94.12 |               52.94 |               76.47 |         82.35 |             1.55 |              7.57 |            0.00 | 60.5/58.5        |
| sgaligner     |      17 |          47.06 |               35.29 |               35.29 |         35.29 |             1.24 |              4.73 |            2.73 | -                |
| sgpgm         |      17 |         100.00 |               17.65 |               17.65 |         17.65 |            80.18 |            145.18 |            2.99 | -                |

Published numbers on the baselines' own protocol (SGAligner sub-scan pairs, not comparable 1:1 with the table above):

| Method | Setting | RRE (deg) | RTE (cm) | RR (%) |
|---|---|---|---|---|
| SGAligner (ICCV'23) | GT graphs, identity init | 1.012 | 1.67 | 99.40 |
| SG-PGM (CVPR'24) | GT graphs, random transform | 1.567 | 3.51 | 98.72 |
| SG-Reg (T-RO'25) | 3RScan-GT pairs | - | - | 82.0 (SG-PGM 79.4 on same) |
| SGAligner++ (2025) | no registration numbers, no code | - | - | - |
