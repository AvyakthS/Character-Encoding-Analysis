# Benchmark Methodology

## 1. Zero-Overhead Verification
To ensure our script measures the *encoding* and not the *script itself*, we run a control test using `cProfile` on the standard `utf-8` loop.
* **Metric:** We require >99% of cumulative execution time to be spent inside `{method 'encode'}` and `{method 'decode'}`.
* **Result:** Consistent validation showing ~0.00s overhead from the benchmark harness.

## 2. The "Warm Cache" Standard
This benchmark explicitly measures **Cached I/O** (System RAM Cache).
* **Process:** All files are read into memory once before the timing loop begins.
* **Reasoning:** This isolates the CPU cost of the encoding from the physical limitations of the NVMe/SSD drive.

## 3. The 20MB Standardization
To compare "Speed per Byte" fairly across different languages, we normalize all datasets to ~20MB.
* **Process:** Source files are purified (stripping invalid characters) and then multiplied until they reach the target size.
* **Reasoning:** 20MB is the "Goldilocks zone" for Python—large enough to saturate the CPU cache but small enough to fit entirely in RAM, avoiding OS paging noise.
