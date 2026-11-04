# Two-visit relocalization (110 pairs)

| method        |   pairs |   returned (%) |   succ@10cm/10° (%) |   succ@20cm/20° (%) |   RR@0.2m (%) |   median RRE (°) |   median RTE (cm) |   mean time (s) | static P/R (%)   |
|:--------------|--------:|---------------:|--------------------:|--------------------:|--------------:|-----------------:|------------------:|----------------:|:-----------------|
| fpfh_ransac   |     110 |         100.00 |               78.18 |               93.64 |         96.36 |             0.96 |              3.70 |            4.83 | -                |
| fpfh_teaser   |     110 |         100.00 |               75.45 |               90.91 |         93.64 |             0.98 |              3.80 |            1.82 | -                |
| ours          |     110 |          93.64 |               72.73 |               89.09 |         91.82 |             0.97 |              4.01 |            0.13 | 72.6/65.6        |
| ours_centroid |     110 |          96.36 |               59.09 |               84.55 |         89.09 |             1.63 |              7.22 |            0.00 | 72.6/65.6        |
| sgaligner     |     110 |          40.91 |               27.27 |               31.82 |         32.73 |             1.45 |              5.44 |            3.37 | -                |
| sgpgm         |     110 |         100.00 |               27.27 |               33.64 |         35.45 |            17.85 |             68.29 |            4.09 | -                |

Published numbers on the baselines' own protocol (SGAligner sub-scan pairs, not comparable 1:1 with the table above):

| Method | Setting | RRE (deg) | RTE (cm) | RR (%) |
|---|---|---|---|---|
| SGAligner (ICCV'23) | GT graphs, identity init | 1.012 | 1.67 | 99.40 |
| SG-PGM (CVPR'24) | GT graphs, random transform | 1.567 | 3.51 | 98.72 |
| SG-Reg (T-RO'25) | 3RScan-GT pairs | - | - | 82.0 (SG-PGM 79.4 on same) |
| SGAligner++ (2025) | no registration numbers, no code | - | - | - |
