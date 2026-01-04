# Changelog

## [v8.0] - The Suite Update (script_v8_fulltestsuite)
**Date:** 2026-01-04
**Focus:** Standardization & UX Polish.
- **Auto-Prep:** Integrated "Auto-Prep" pipeline to purify and multiply datasets to exactly 20MB.
- **UX:** Implemented "Quiet Generation" and dynamic table column widths.
- **Cleanup:** Removed redundant "Raw Data" tables from console output.

## [v7.0] - The Utility Update (script_v7_versatilitymeansutility)
**Date:** 2025-11-20
**Focus:** Flexibility & Safety.
- **Auto-Discovery:** Replaced hardcoded lists with `glob` directory scanning.
- **Safety:** Implemented `text.isascii()` to flag incompatible encodings with `(Data Loss!)`.

## [v6.0] - The Reliability Update (script_v6_stablecore)
**Date:** 2025-11-11
**Focus:** Validation & Logging.
- **Logging:** Added `Logger` class for dual console/file output.
- **Validation:** Integrated `cProfile` to prove zero-overhead measurement.

## [v5.0] - The Visuals Update (script_v5_sleekvisuals)
**Date:** 2025-11-11
**Focus:** Reporting Standards.
- **UI:** Implemented Unicode box-drawing tables.
- **Metrics:** Added "vs. Baseline" comparison columns.

## [v4.0] - The Isolation Update (script_v4_rwisolation)
**Date:** 2025-11-11
**Focus:** Methodology.
- **Science:** Separated "Write" and "Read" loops to isolate I/O variables.
- **Refactor:** Decoupled Encode/Decode logic in CPU tests.

## [v3.0] - The Precision Update (script_v3_tracemalloc)
**Date:** 2025-11-11
**Focus:** Memory Metrics.
- **Metrics:** Switched from `psutil` to `tracemalloc` for precise <1MB memory tracking.

## [v2.0] - The Architecture Update (script_v2_splitarch)
**Date:** 2025-11-10
**Focus:** Modularization.
- **Structure:** Split monolithic script into distinct I/O and CPU test suites.

## [v1.0] - The Prototype (script_v1_prototype)
**Date:** 2025-11-01
**Focus:** Proof of Concept.
- Initial implementation of read/write/encode/decode timing loops.
