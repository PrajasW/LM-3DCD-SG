# Two-visit relocalization (22 pairs)

| method        |   pairs |   returned (%) |   succ@10cm/10° (%) |   succ@20cm/20° (%) |   RR@0.2m (%) |   median RRE (°) |   median RTE (cm) |   mean time (s) | static P/R (%)   |
|:--------------|--------:|---------------:|--------------------:|--------------------:|--------------:|-----------------:|------------------:|----------------:|:-----------------|
| fpfh_ransac   |      22 |         100.00 |               81.82 |               95.45 |         95.45 |             1.18 |              4.47 |            1.63 | -                |
| fpfh_teaser   |      22 |         100.00 |               81.82 |               95.45 |         95.45 |             1.18 |              4.47 |            0.93 | -                |
| ours          |      22 |          86.36 |               77.27 |               86.36 |         86.36 |             0.98 |              3.64 |            0.07 | 72.5/69.9        |
| ours_centroid |      22 |          86.36 |               45.45 |               81.82 |         86.36 |             2.33 |              9.27 |            0.00 | 72.5/69.9        |

Published numbers on the baselines' own protocol (SGAligner sub-scan pairs, not comparable 1:1 with the table above):

| Method | Setting | RRE (deg) | RTE (cm) | RR (%) |
|---|---|---|---|---|
| SGAligner (ICCV'23) | GT graphs, identity init | 1.012 | 1.67 | 99.40 |
| SG-PGM (CVPR'24) | GT graphs, random transform | 1.567 | 3.51 | 98.72 |
| SG-Reg (T-RO'25) | 3RScan-GT pairs | - | - | 82.0 (SG-PGM 79.4 on same) |
| SGAligner++ (2025) | no registration numbers, no code | - | - | - |
