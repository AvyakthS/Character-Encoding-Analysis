# Research Journal & Learnings

## 1. The UTF-8 Memory Anomaly (Solved)
* **Observation:** In `v3` through `v7`, small ASCII files (0.8MB) consumed ~3x their size in RAM during UTF-8 processing.
* **Hypothesis:** Python's encoder uses a pessimistic pre-allocation strategy (3-4 bytes per char) for UTF-8.
* **Resolution:** In `v8`, testing with 20MB files proved this is a fixed overhead, not a linear leak. Large files showed a near 1:1 memory ratio.

## 2. The CJK Storage Efficiency
* **Finding:** For pure Chinese text, `utf-16` is consistently ~33% smaller than `utf-8`.
* **Implication:** `utf-16` is the scientifically superior storage format for East Asian databases, contrary to the "always use utf-8" best practice.

## 3. The CPU Decoding Tax
* **Finding:** Decoding `utf-8` text is significantly slower (up to 7x slower) than decoding `utf-32` or `ascii`.
* **Reason:** `utf-8` requires bitwise validation for every character sequence (variable width), whereas `utf-32` is a simple memory offset calculation (fixed width).
