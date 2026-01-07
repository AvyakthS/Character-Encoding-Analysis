# Project Changelog

## [v9.0.0] - The "Fancy" Release
* **Methodology:** Implemented **Adaptive Timing**. Tests now target a 2.0-second runtime instead of fixed iterations, ensuring accuracy across all speed classes.
* **Performance:** Added **Parallel Dataset Generation** using `ThreadPoolExecutor` to speed up the startup phase.
* **Visualisation:** Integrated `matplotlib` to automatically generate PNG charts for Storage, Speed, and Memory.
* **Bug Fix:** Fixed a reporting index error where English test results were mislabeled in the final summary table.

## [v8.0.0] - The "Analysis" Release
* **Research Focus:** Standardisation of Methodology.
* **Feature:** Implemented the **"Auto-Prep Pipeline"** to normalise all datasets to **20MB**, ensuring fair comparisons.
* **Output:** Generates the final comparative tables for the report.

## [v7.0.0] - The "Utility" Release
* **Research Focus:** Dataset Collection.
* **Feature:** Added `glob` auto-discovery to ingest user-provided raw data files automatically.
* **Safety:** Added `isascii()` checks to verify backward compatibility.

## [v4.0.0] - The "Isolation" Release
* **Research Focus:** Read/Write Performance.
* **Feature:** Decoupled "Write" loops from "Read" loops to prevent OS write-buffering from skewing the speed analysis.

## [v3.0.0] - The "Precision" Release
* **Research Focus:** Memory Efficiency.
* **Feature:** Replaced OS-level monitoring with `tracemalloc` to capture byte-level memory usage differences.

## [v1.0.0] - The Prototype
* **Research Focus:** Initial Implementation.
* **Feature:** Basic Python script to write datasets to disk in multiple formats.