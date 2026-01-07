# Experimental Methodology

This document details the technical implementation of the research plan, corresponding to the "Methodology" section of the original proposal.

## Step 1: Dataset Collection & Parallel Standardization
To ensure statistical validity, we employed an **Auto-Prep Pipeline**.

* **Intent Detection:** The system automatically categorizes input text into "ASCII", "CJK", or "Emoji" buckets.
* **Parallel Generation:** Using `ThreadPoolExecutor`, the system purifies inputs (stripping invalid chars) and multiplies content to reach a standardized **20 MB**.

> **Reasoning:** Comparing a 1KB file against a 1MB file introduces variance due to OS caching. **20MB** is large enough to saturate CPU caches (L3) while fitting safely in RAM.

## Step 2: Adaptive Benchmarking Engine (v9.0)
Previous iterations used fixed loop counts (e.g., 1000 loops), which wasted time on slow tests and under-sampled fast tests.

### The Solution: Adaptive Timing
We implemented a dynamic timing system to normalize test duration.

* **Logic:** The script runs a "Probe" set of 100 iterations. It calculates the operations per second and extends the test duration dynamically to meet a **2.0-second target**.
* **Benefit:** This ensures that trivial operations (like ASCII decoding) get millions of samples, while heavy operations (like UTF-8 Emoji decoding) get just enough to be statistically valid, without freezing the machine.

## Step 3: Performance Metrics
* **Storage (Metric A):** Uses `os.path.getsize()` to measure the exact byte count.
* **Memory (Metric B):** Replaced standard OS polling with `tracemalloc`. This tracks Python's internal memory allocator, allowing us to see the exact cost of the encoding objects and the "Memory Spike" caused by internal UCS-4 conversion.
* **Speed (Metric C):** Uses `time.perf_counter()` for nanosecond-precision timing of the Read/Write loops.

## Step 4: Verification Standards
* **I/O Isolation:** Read and Write operations are performed in separate loops to prevent OS write-buffering from skewing read metrics.
* **Zero-Overhead Validation:** We run a `cProfile` trace to ensure **>99%** of the execution time is spent in the actual encode/decode functions, ensuring the benchmark tool itself is not skewing the results.