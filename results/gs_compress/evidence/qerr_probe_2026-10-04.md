# S0.5 量化误差探针（G1 整改：直测机制核心主张，q=0.1%）

> 零 GPU，直接在 PLY 上算 quantize→dequantize 的 MSE（不渲染）。
> `ratio_full = mse_v2 / mse_v1`（<1 = 稳健范围降低量化误差）。

| seq | arm | 组 | span_full | span_robust | tail% | mse_v1 | ratio_full | ratio_esc |
|---|---|---|---|---|---|---|---|---|
| balloon | baseline | xyz | 10.8945 | 8.6013 | 0.202 | 2.313e-09 | 90626.0290 | 0.6212 |
| balloon | baseline | f_dc | 6.5525 | 4.8332 | 0.199 | 5.506e-05 | 6.5535 | 0.5401 |
| balloon | baseline | opacity | 27.0520 | 24.6300 | 0.202 | 9.403e-04 | 1.6874 | 0.8226 |
| balloon | baseline | scale | 11.0011 | 5.9341 | 0.202 | 1.552e-04 | 7.7342 | 0.2885 |
| balloon | baseline | rot3 | 3.2129 | 1.6411 | 0.202 | 1.327e-05 | 7.8279 | 0.2593 |
| crowd2 | baseline | xyz | 12.5812 | 9.7640 | 0.200 | 3.067e-09 | 85436.6330 | 0.6027 |
| crowd2 | baseline | f_dc | 7.4585 | 5.3306 | 0.200 | 7.220e-05 | 6.8390 | 0.5004 |
| crowd2 | baseline | opacity | 26.7257 | 24.6672 | 0.204 | 9.171e-04 | 1.5386 | 0.8451 |
| crowd2 | baseline | scale | 12.3608 | 5.7498 | 0.200 | 1.952e-04 | 8.6266 | 0.2174 |
| crowd2 | baseline | rot3 | 3.2786 | 1.9263 | 0.200 | 1.384e-05 | 6.3880 | 0.3436 |
| person_tracking | baseline | xyz | 12.6578 | 8.7600 | 0.200 | 3.100e-09 | 322722.8583 | 0.4802 |
| person_tracking | baseline | f_dc | 8.5517 | 5.7500 | 0.199 | 9.356e-05 | 3.7445 | 0.4522 |
| person_tracking | baseline | opacity | 26.8696 | 25.2913 | 0.198 | 9.257e-04 | 1.1539 | 0.8808 |
| person_tracking | baseline | scale | 9.4907 | 5.9186 | 0.200 | 1.150e-04 | 4.0123 | 0.3903 |
| person_tracking | baseline | rot3 | 3.0980 | 1.8758 | 0.200 | 1.228e-05 | 5.9262 | 0.3661 |
| crowd3 | final | xyz | 12.8062 | 9.6680 | 0.200 | 3.187e-09 | 148298.4511 | 0.5663 |
| crowd3 | final | f_dc | 9.9357 | 5.8900 | 0.184 | 1.262e-04 | 9.8181 | 0.3511 |
| crowd3 | final | opacity | 15.9902 | 13.3027 | 0.202 | 3.286e-04 | 2.7016 | 0.6928 |
| crowd3 | final | scale | 12.6909 | 6.1158 | 0.200 | 2.068e-04 | 13.1498 | 0.2321 |
| crowd3 | final | rot3 | 3.5301 | 2.1717 | 0.200 | 1.595e-05 | 7.9769 | 0.3790 |
| person_tracking2 | final | xyz | 13.4712 | 10.0046 | 0.201 | 3.528e-09 | 93442.9038 | 0.5484 |
| person_tracking2 | final | f_dc | 10.3657 | 6.4995 | 0.199 | 1.364e-04 | 7.4688 | 0.3929 |
| person_tracking2 | final | opacity | 19.2751 | 13.6735 | 0.201 | 4.748e-04 | 3.4857 | 0.5033 |
| person_tracking2 | final | scale | 11.2067 | 6.1614 | 0.201 | 1.608e-04 | 5.9306 | 0.3031 |
| person_tracking2 | final | rot3 | 3.7942 | 2.1632 | 0.201 | 1.849e-05 | 4.4300 | 0.3222 |

| seq | arm | 加权 ratio_full |
|---|---|---|
| balloon | baseline | 13207.9634 |
| crowd2 | baseline | 12451.8864 |
| person_tracking | baseline | 47014.9115 |
| crowd3 | final | 21611.6015 |
| person_tracking2 | final | 13616.2866 |