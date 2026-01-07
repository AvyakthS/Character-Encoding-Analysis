# Research Journal
*A chronological record of the experiments conducted to satisfy the project requirements.*

## Phase 1: Establishing the Baseline (Steps 1 & 2)
* **Objective:** Implement the basic file I/O program.
* **Action:** Created `script_v1` to write English and Multilingual text to ASCII, UTF-8, UTF-16, and UTF-32.
* **Observation:** Initial results showed erratic timings. Small files (10KB) were processing too fast to measure accurately.

## Phase 2: The Memory Investigation (Metric B)
* **Objective:** Analyze Memory Efficiency.
* **Action:** Switched to `tracemalloc` in v3.
* **Discovery:** We observed a massive overhead in UTF-8 for small files. This was initially thought to be an inefficiency, but Phase 3 proved it was a fixed interpreter startup cost.

## Phase 3: The Performance Analysis (Metric C)
* **Objective:** Analyze Read/Write Speed.
* **Action:** Separated I/O tests (Disk) from CPU tests (In-Memory) in v4.
* **Discovery:** We isolated the **"UTF-8 CPU Tax."** Decoding UTF-32 is nearly instant (`0.002s`) compared to UTF-8 (`0.017s`) for complex text because the CPU can skip directly to characters in fixed-width encodings.

## Phase 4: Standardization (v8)
* **Objective:** Produce final Comparative Analysis Tables.
* **Action:** Built the **Auto-Prep Suite** to standardize files to **20MB**.
* **Outcome:** Successfully verified the CJK storage savings (**~33% smaller files** with UTF-16).

## Phase 5: The Visual & Adaptive Era (v9)
* **Objective:** Visualization and Optimization.
* **Action:** Implemented `Matplotlib` chart generation and **Adaptive Timing** (2.0s target).
* **Discovery (The Multilingual Spike):** We found that mixed-language files cause Python to spike RAM usage by **400%** (79MB RAM for a 20MB file). This confirms that Python upgrades mixed strings to a fixed-width 4-byte internal representation (UCS-4) to support *O(1)* indexing, regardless of the output encoding.
* **Correction:** Fixed an indexing bug in the reporting engine where the "English" table was pulling data from the wrong dataset row.