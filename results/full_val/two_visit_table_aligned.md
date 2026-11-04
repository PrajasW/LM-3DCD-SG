# Two-visit relocalization (110 pairs)

| method        |   pairs |   returned (%) |   succ@10cm/10° (%) |   succ@20cm/20° (%) |   RR@0.2m (%) |   median RRE (°) |   median RTE (cm) |   mean time (s) | static P/R (%)   |
|:--------------|--------:|---------------:|--------------------:|--------------------:|--------------:|-----------------:|------------------:|----------------:|:-----------------|
| fpfh_ransac   |     110 |         100.00 |               83.64 |               92.73 |         95.45 |             0.95 |              3.37 |            4.67 | -                |
| fpfh_teaser   |     110 |         100.00 |               81.82 |               90.91 |         93.64 |             0.97 |              3.38 |            1.78 | -                |
| ours          |     110 |          93.64 |               78.18 |               89.09 |         91.82 |             0.98 |              3.28 |            0.13 | 72.6/65.6        |
| ours_centroid |     110 |          96.36 |               69.09 |               83.64 |         89.09 |             1.63 |              5.93 |            0.00 | 72.6/65.6        |
| sgaligner     |     110 |          80.00 |               71.82 |               79.09 |         80.00 |             0.81 |              3.03 |            8.26 | -                |
| sgpgm         |     110 |         100.00 |               66.36 |               74.55 |         72.73 |             1.10 |              4.46 |            4.14 | -                |

Published numbers on the baselines' own protocol (SGAligner sub-scan pairs, not comparable 1:1 with the table above):

| Method | Setting | RRE (deg) | RTE (cm) | RR (%) |
|---|---|---|---|---|
| SGAligner (ICCV'23) | GT graphs, identity init | 1.012 | 1.67 | 99.40 |
| SG-PGM (CVPR'24) | GT graphs, random transform | 1.567 | 3.51 | 98.72 |
| SG-Reg (T-RO'25) | 3RScan-GT pairs | - | - | 82.0 (SG-PGM 79.4 on same) |
| SGAligner++ (2025) | no registration numbers, no code | - | - | - |
