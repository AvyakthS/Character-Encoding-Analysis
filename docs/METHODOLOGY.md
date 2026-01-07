# 🧪 Experimental Methodology
*This document details the technical implementation and verification standards used to validate the findings presented in the README.*

---

## ⚙️ 1. Dataset Collection & Standardisation
### The Auto-Prep Pipeline
To ensure statistical validity, we rejected the use of arbitrary user files directly. Instead, we implemented an **Auto-Prep Pipeline**:

* **Intent Detection:** The system parses filenames to categorise content into "ASCII", "CJK", or "Emoji" buckets.
* **Purification:** Input text is stripped of invalid characters that do not match the intent (e.g., removing ASCII noise from a CJK test).
* **Standardisation:** Content is multiplied to reach a specific target of **20.0 MB**.

> **Reasoning:** Comparing a 5KB config file against a 10MB novel introduces variance due to OS caching and allocator latency. **20MB** is the "Goldilocks Zone"—large enough to saturate CPU L3 caches, but small enough to fit safely in RAM without triggering disk swapping.

---

## ⏱️ 2. Adaptive Benchmarking Engine
Previous iterations used fixed loop counts, which led to under-sampling of fast operations (like ASCII read) and excessive runtimes for slow operations.

### Adaptive Logic
The `v9` engine performs a "Probe" run (100 iterations) to calculate operations-per-second. It then dynamically extends the test duration to meet a **2.0-second target**.

> **Result:** This ensures that trivial operations are sampled thousands of times, while heavy operations are sampled enough to be statistically significant, normalizing the error margin across all tests.

---

## 📏 3. Variable Isolation & Metrics

### 💾 I/O Isolation
Read and Write operations are performed in **distinct loops**. Files are written, closed, and flushed before the "Read" timer begins to prevent OS write-buffering from artificially inflating read speeds.

### 🧠 Memory Tracing
We replaced standard OS polling (`psutil`) with `tracemalloc`. This hooks into Python's internal memory allocator (`pymalloc`), allowing us to measure the exact size of Python objects in memory, independent of the Operating System's page size.

---

## ✅ 4. Verification Standards (Zero-Overhead)
To ensure the benchmark tool itself does not skew the results, we integrated `cProfile` validation.

* **The Standard:** We require that **>99%** of the cumulative execution time is spent inside the built-in `{method 'encode'}` and `{method 'decode'}` functions.
* **Validation:** If the benchmarking harness (logging, loops, overhead) exceeds **1%** of the runtime, the data is flagged as invalid.

---

## 💻 5. System Specifications

* **Runtime:** Python 3.14 (CPython)
* **Operating System** Pop!_OS 24.04 LTS
* **Kernel:** Linux 6.17 (Modified for Pop!_OS)
* **Hardware Target:** A 1TB WD Black SN7100 PCIE4.0 NVME SSD (for I/O throughput) paired with 32GB DDR5 SODIMM RAM and a 8-core AMD 8845HS CPU (for CPU encoding).