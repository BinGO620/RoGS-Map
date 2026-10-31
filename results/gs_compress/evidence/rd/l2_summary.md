# L2 R-D 主表（baseline+final × Bonn 7 × 3 seed）

## 近无损工作点 16/8/8/8/8

| seq | arm | ratio | B/prim | PSNR | static | ghost |
|---|---|---|---|---|---|---|
| balloon | baseline | 5.85x | 13.68 | 15.163 | 23.950 | 2.157 |
| balloon | final | 5.94x | 13.48 | 15.502 | 24.723 | 2.342 |
| balloon2 | baseline | 6.00x | 13.34 | 15.155 | 20.029 | -3.058 |
| balloon2 | final | 5.82x | 13.76 | 14.626 | 19.695 | -3.154 |
| crowd | baseline | 6.01x | 13.31 | 21.819 | 22.889 | 2.256 |
| crowd | final | 6.03x | 13.28 | 21.834 | 22.888 | 4.141 |
| crowd2 | baseline | 6.18x | 12.95 | 13.473 | 25.054 | -1.852 |
| crowd2 | final | 6.07x | 13.19 | 13.082 | 22.564 | -3.939 |
| crowd3 | baseline | 6.06x | 13.20 | 13.881 | 22.703 | -0.951 |
| crowd3 | final | 6.03x | 13.26 | 13.914 | 22.759 | -0.461 |
| person_tracking | baseline | 5.86x | 13.65 | 13.220 | 18.302 | -1.827 |
| person_tracking | final | 5.84x | 13.70 | 13.714 | 19.524 | -1.733 |
| person_tracking2 | baseline | 5.85x | 13.69 | 14.782 | 19.389 | 2.310 |
| person_tracking2 | final | 5.88x | 13.61 | 15.013 | 20.602 | -0.227 |

**near_lossless** 全局：ratio 5.96x, PSNR 15.370, static 21.791, ghost -0.285

**mid** 全局：ratio 8.77x, PSNR 15.322, static 21.637, ghost -0.286

**aggressive** 全局：ratio 15.11x, PSNR 14.740, static 19.209, ghost 0.155