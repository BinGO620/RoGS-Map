## RGB-D Datasets

| Source | Type | Full Name | Abbreviation |
|:---|:---:|:---|:---|
| **TUM** | 🟢 Static | `rgbd_dataset_freiburg1_desk` | `f1_desk` |
| | | `rgbd_dataset_freiburg2_xyz` | `f2_xyz` |
| | | `rgbd_dataset_freiburg3_long_office_household` | `f3_office` |
| **TUM** | 🟡 Dynamic | `rgbd_dataset_freiburg2_desk_with_person` | `f2_person` |
| | | `rgbd_dataset_freiburg3_sitting_halfsphere` | `f3_st_hf` |
| | | `rgbd_dataset_freiburg3_sitting_rpy` | `f3_st_rpy` |
| | | `rgbd_dataset_freiburg3_sitting_xyz` | `f3_st_xyz` |
| | | `rgbd_dataset_freiburg3_walking_halfsphere` | `f3_wk_hf` |
| | | `rgbd_dataset_freiburg3_walking_rpy` | `f3_wk_rpy` |
| | | `rgbd_dataset_freiburg3_walking_xyz` | `f3_wk_xyz` |
| **BONN** | 🔴 Dynamic | `rgbd_bonn_balloon` | `balloon` |
| | | `rgbd_bonn_balloon2` | `balloon2` |
| | | `rgbd_bonn_crowd` | `crowd` |
| | | `rgbd_bonn_crowd2` | `crowd2` |
| | | `rgbd_bonn_moving_nonobstructing_box` | `mv_no_box` |
| | | `rgbd_bonn_moving_nonobstructing_box2` | `mv_no_box2` |
| | | `rgbd_bonn_person_tracking` | `person_t` |
| | | `rgbd_bonn_person_tracking2` | `person_t2` |

## Camera Intrinsics

| Dataset Group | Resolution | $f_x$ | $f_y$ | $c_x$ | $c_y$ | Distortion Coefficients |
|:---|:---:|---:|---:|---:|---:|:---|
| **TUM f1** | 640 × 480 | 517.3 | 516.5 | 318.6 | 255.3 | $[0.2624,\ -0.9531,\ -0.0054,\ 0.0026,\ 1.1633]$ |
| **TUM f2** | 640 × 480 | 520.9 | 521.0 | 325.1 | 249.7 | $[0.2312,\ -0.7849,\ -0.0033,\ -0.0001,\ 0.9172]$ |
| **TUM f3** | 640 × 480 | 535.4 | 539.2 | 320.1 | 247.6 | $[0,\ 0,\ 0,\ 0,\ 0]$ |
| **BONN** | 640 × 480 | 542.82 | 542.58 | 315.59 | 237.76 | $[0.0399,\ -0.0993,\ -0.0007,\ -0.0001,\ 0]$ |

> **Notes:**
> - Distortion coefficients follow the order: $[k_1,\ k_2,\ p_1,\ p_2,\ k_3]$ (Brown–Conrady model).
> - TUM fr3 and BONN use rectified / linearized images (near-zero distortion).