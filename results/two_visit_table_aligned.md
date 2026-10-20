# Two-visit relocalization (17 pairs)

| method        |   pairs |   returned (%) |   succ@10cm/10° (%) |   succ@20cm/20° (%) |   RR@0.2m (%) |   median RRE (°) |   median RTE (cm) |   mean time (s) | static P/R (%)   |
|:--------------|--------:|---------------:|--------------------:|--------------------:|--------------:|-----------------:|------------------:|----------------:|:-----------------|
| fpfh_ransac   |      17 |         100.00 |               88.24 |               88.24 |         88.24 |             1.09 |              2.42 |            4.73 | -                |
| fpfh_teaser   |      17 |         100.00 |               82.35 |               82.35 |         82.35 |             1.09 |              2.42 |            1.67 | -                |
| ours          |      17 |          94.12 |               82.35 |               82.35 |         82.35 |             0.99 |              2.42 |            0.16 | 60.5/58.5        |
| ours_centroid |      17 |          94.12 |               76.47 |               82.35 |         82.35 |             1.55 |              5.78 |            0.00 | 60.5/58.5        |
| sgaligner     |      17 |          70.59 |               70.59 |               70.59 |         70.59 |             0.83 |              2.23 |            6.10 | -                |
| sgpgm         |      17 |         100.00 |               64.71 |               64.71 |         64.71 |             1.53 |              4.93 |            2.88 | -                |

Published numbers on the baselines' own protocol (SGAligner sub-scan pairs, not comparable 1:1 with the table above):

| Method | Setting | RRE (deg) | RTE (cm) | RR (%) |
|---|---|---|---|---|
| SGAligner (ICCV'23) | GT graphs, identity init | 1.012 | 1.67 | 99.40 |
| SG-PGM (CVPR'24) | GT graphs, random transform | 1.567 | 3.51 | 98.72 |
| SG-Reg (T-RO'25) | 3RScan-GT pairs | - | - | 82.0 (SG-PGM 79.4 on same) |
| SGAligner++ (2025) | no registration numbers, no code | - | - | - |
