# Neural Implicit SLAM Efficiency Notes

This note summarizes observations from the RoDyn-SLAM reproduction that may be
useful when discussing limitations of neural implicit SLAM methods.

## Main Point

Neural implicit SLAM methods often have a heavy initialization and mapping cost.
Unlike feature-based SLAM, which can initialize a sparse map from detected
features, neural implicit methods usually optimize a scene representation from
RGB-D observations. This turns mapping into an iterative training problem.

In practice, the first frame can be especially slow because the method must
initialize the neural scene field before normal tracking and mapping can proceed.

## RoDyn-SLAM Example

In this RoDyn-SLAM reproduction, the first frame is handled by
`first_frame_mapping()` in `rodynslam.py`. The relevant configuration is in
`configs/Tum/tum.yaml`:

```yaml
mapping:
  first_iters: 2000
  sample: 2048
  first_mesh: True
training:
  n_samples: 64
  n_samples_d: 64
```

This means the first frame is not a simple one-pass operation. It performs many
optimization steps over sampled rays, computes RGB/depth/SDF/free-space losses,
and backpropagates through the neural implicit representation.

RoDyn-SLAM also extracts a mesh after first-frame mapping when
`mapping.first_mesh` is enabled. The logs show:

```text
First frame mapping...
Running Marching Cubes
Mesh saved
First frame mapping done
```

This mesh extraction adds extra initialization cost.

## Why It Is Slow

The first-frame cost comes from several factors:

- The scene representation is a neural field rather than an explicit sparse map.
- Each optimization iteration samples pixels/rays and evaluates the implicit
  field along sampled points.
- RGB, depth, SDF, and free-space losses require forward and backward passes.
- Dynamic-scene handling uses segmentation masks and distance maps to bias
  sampling toward reliable/static regions.
- Mesh extraction via marching cubes can be expensive.

These costs are structural to neural implicit SLAM. They are not simply caused
by poor GPU memory usage.

## Parallel Execution Observation

Running multiple RoDyn-SLAM jobs in parallel did not exhaust GPU memory on the
RTX 4090, but it still slowed first-frame progress. This suggests the bottleneck
is not only peak memory. Parallel neural implicit SLAM jobs can also compete for:

- CUDA kernel scheduling
- GPU memory bandwidth
- tiny-cuda-nn/hash-grid kernels
- CPU dataloader and OpenMP/BLAS threads
- Python multiprocessing and IO

Therefore, low GPU memory usage or low instantaneous GPU utilization does not
necessarily mean that more parallel jobs will scale linearly.

## Reproduction Observation

During this reproduction, completed RoDyn-SLAM runs used only about 1.1-1.2 GB
peak GPU memory per run, but the end-to-end FPS was low. For example, completed
TUM runs showed approximately:

```text
f1_desk:   about 0.43-0.45 FPS
f2_xyz:    about 0.45-0.47 FPS
f3_office: about 0.27 FPS
```

This illustrates an important point: neural implicit SLAM may have modest peak
GPU memory use while still being computationally slow due to iterative
optimization.

## Suggested Paper Wording

Neural implicit SLAM methods provide compact continuous scene representations
and can support high-quality reconstruction, but their mapping process is often
optimization-heavy. In RoDyn-SLAM, for example, the first frame is used to
initialize a neural SDF/color field through thousands of gradient-based updates
before regular tracking and mapping can proceed. This makes the initialization
stage substantially slower than sparse feature-based SLAM pipelines. The cost is
further increased by dynamic-scene masking, ray sampling, SDF/free-space losses,
and optional mesh extraction. As a result, neural implicit SLAM can show low
end-to-end FPS even when peak GPU memory consumption is moderate.

## Practical Implication

For fair evaluation, efficiency metrics such as FPS and runtime should be
reported carefully. If neural implicit SLAM jobs are run concurrently with other
GPU workloads, the reported FPS may be distorted by resource contention. Such
conditions should be noted in raw result files and experiment reports.
