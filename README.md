Character Encoding Analysis
A comprehensive benchmarking suite designed to scientifically analyze how Python handles text encodings (ASCII, UTF-8, UTF-16, UTF-32) across storage, memory, and CPU cycles.

This project moves beyond theoretical "Big O" notation to measure real-world performance, uncovering specific behaviors like the UTF-8 Decoding Tax, CJK Storage Efficiency, and the internal memory allocation strategies of the CPython runtime.

🚀 Key Features
Scientific Rigor: Uses tracemalloc for byte-precise memory tracking and cProfile to validate zero-overhead measurement.

Variable Isolation: Separates "Disk-Bound" I/O tests from "CPU-Bound" In-Memory tests to prevent bottleneck pollution.

Smart Auto-Prep: The v8 suite automatically detects file intent (ASCII vs. Emoji vs. CJK), purifies the content, and standardizes datasets to exactly 20MB for fair comparison.

Cross-Platform: Fully compatible with Linux (Pop!_OS) and Windows 11 terminals.

Evolutionary History: Includes the entire development history (v1 through v8), allowing users to trace the evolution of the benchmarking methodology.

📂 Project Structure
The project uses a sandboxed architecture to separate code, user data, and generated artifacts.

Plaintext

/Character Encoding Analysis/
├── versions/                            # The Benchmark Scripts
│   ├── script_v1_prototype/             # The original proof-of-concept
│   ├── script_v2_splitarch/             # Split I/O and CPU testing
│   ├── script_v3_tracemalloc/           # Introduction of precise memory tracking
│   ├── script_v4_rwisolation/           # Separation of Read vs. Write loops
│   ├── script_v5_sleekvisuals/          # Introduction of box-drawing tables
│   ├── script_v6_stablecore/            # The stable "Manual Config" tool
│   ├── script_v7_versalitymeansutility/ # The "Auto-Detect" tool
│   └── script_v8_fulltestsuite/         # The FINAL "Auto-Prep" Suite (Recommended)
│
├── user_bench_files_freesize/           # INPUT: Drop your raw .txt files here
│   ├── english.txt
│   ├── cjk_journey.txt
│   └── ...
│
├── user_bench_files_standardized/       # OUTPUT: The suite generates clean 20MB files here
│   ├── english_bench.txt
│   └── ...
│
└── docs/                                # Documentation
    ├── CHANGELOG.md                     # Version history
    ├── METHODOLOGY.md                   # Scientific defense of the methods
    └── JOURNAL.md                       # Key findings and research notes
🛠️ Installation & Usage
1. Requirements
Python 3.8+

psutil library (for CPU load monitoring)

Bash

pip install psutil
2. Setup Data
Place your raw source text files into the user_bench_files_freesize/ directory.

Tip: Use diverse datasets (e.g., one pure ASCII file, one Chinese novel, one Emoji list) to see the most interesting results.

3. Run the Benchmark
Navigate to the version you wish to run. We recommend v8 for the most accurate, standardized results.

Bash

cd "Character Encoding Analysis/versions/script_v8_fulltestsuite"
python script_v8_fulltestsuite.py
The script will:

Scan your freesize folder.

Purify & Standardize files to 20MB (saved to standardized folder).

Benchmark every file against ASCII, UTF-8, UTF-16, and UTF-32.

Report full statistics to the console and analysis_report.txt.

🧠 Key Findings Summary
The "UTF-8 Tax": Decoding UTF-8 text is significantly slower (up to 7x) than decoding UTF-32 or ASCII due to the CPU overhead of validating variable-length byte sequences.

Memory Efficiency: Contrary to early hypotheses, Python's UTF-8 encoder is highly efficient at scale, showing near 1:1 memory usage for large files (solving the "small file anomaly").

CJK Storage: For East Asian languages, UTF-16 is the scientifically superior storage format, reducing file size by ~33% compared to UTF-8.

For detailed research notes, read docs/JOURNAL.md.

📜 Methodology
This benchmark adheres to strict standards to ensure validity:

Warm Cache I/O: Measures the maximum throughput of the OS file cache, eliminating disk hardware variance.

20MB Normalization: Standardizes all datasets to ~20MB to balance CPU saturation with RAM safety.

Zero-Overhead: Verified via cProfile to ensure >99% of execution time is spent in the actual encode/decode methods.

For the full defense of these methods, read docs/METHODOLOGY.md.

Author: Avyakths License: Open Source
