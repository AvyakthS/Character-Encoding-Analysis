# **Character Encoding Analysis**

A comprehensive benchmarking suite designed to scientifically analyze how Python handles text encodings (ASCII, UTF-8, UTF-16, UTF-32) across storage, memory, and CPU cycles.

This project moves beyond theoretical "Big O" notation to measure real-world performance, uncovering specific behaviors like the UTF-8 Decoding Tax, CJK Storage Efficiency, and the internal memory allocation strategies of the CPython runtime.

## **🚀 Key Features**

* **Scientific Rigor:** Uses tracemalloc for byte-precise memory tracking and cProfile to validate zero-overhead measurement.  
* **Variable Isolation:** Separates "Disk-Bound" I/O tests from "CPU-Bound" In-Memory tests to prevent bottleneck pollution.  
* **Smart Auto-Prep:** The v8 suite automatically detects file intent (ASCII vs. Emoji vs. CJK), purifies the content, and standardizes datasets to exactly 20MB for fair comparison.  
* **Cross-Platform:** Fully compatible with Linux (Pop\!\_OS) and Windows 11 terminals.  
* **Evolutionary History:** Includes the entire development history (v1 through v8), allowing users to trace the evolution of the benchmarking methodology.

## **📂 Project Structure**

The project uses a sandboxed architecture to separate code, user data, and generated artifacts.

/Character Encoding Analysis/  
├── versions/                            \# The Benchmark Scripts  
│   ├── script\_v1\_prototype/             \# The original proof-of-concept  
│   ├── script\_v2\_splitarch/             \# Split I/O and CPU testing  
│   ├── script\_v3\_tracemalloc/           \# Introduction of precise memory tracking  
│   ├── script\_v4\_rwisolation/           \# Separation of Read vs. Write loops  
│   ├── script\_v5\_sleekvisuals/          \# Introduction of box-drawing tables  
│   ├── script\_v6\_stablecore/            \# The stable "Manual Config" tool  
│   ├── script\_v7\_versalitymeansutility/ \# The "Auto-Detect" tool  
│   └── script\_v8\_fulltestsuite/         \# The FINAL "Auto-Prep" Suite (Recommended)  
│  
├── user\_bench\_files\_freesize/           \# INPUT: Drop your raw .txt files here  
│   ├── english.txt  
│   ├── cjk\_journey.txt  
│   └── ...  
│  
├── user\_bench\_files\_standardized/       \# OUTPUT: The suite generates clean 20MB files here  
│   ├── english\_bench.txt  
│   └── ...  
│  
└── docs/                                \# Documentation  
    ├── CHANGELOG.md                     \# Version history  
    ├── METHODOLOGY.md                   \# Scientific defense of the methods  
    └── JOURNAL.md                       \# Key findings and research notes

## **🛠️ Installation & Usage**

### **1\. Requirements**

* Python 3.8+  
* psutil library (for CPU load monitoring)

pip install psutil

### **2\. Setup Data**

Place your raw source text files into the user\_bench\_files\_freesize/ directory.

**Tip:** Use diverse datasets (e.g., one pure ASCII file, one Chinese novel, one Emoji list) to see the most interesting results.

### **3\. Run the Benchmark**

Navigate to the version you wish to run. We recommend **v8** for the most accurate, standardized results.

cd "Character Encoding Analysis/versions/script\_v8\_fulltestsuite"  
python script\_v8\_fulltestsuite.py

The script will:

1. Scan your freesize folder.  
2. Purify & Standardize files to 20MB (saved to standardized folder).  
3. Benchmark every file against ASCII, UTF-8, UTF-16, and UTF-32.  
4. Report full statistics to the console and analysis\_report.txt.

## **🧠 Key Findings Summary**

* **The "UTF-8 Tax":** Decoding UTF-8 text is significantly slower (up to 7x) than decoding UTF-32 or ASCII due to the CPU overhead of validating variable-length byte sequences.  
* **Memory Efficiency:** Contrary to early hypotheses, Python's UTF-8 encoder is highly efficient at scale, showing near 1:1 memory usage for large files (solving the "small file anomaly").  
* **CJK Storage:** For East Asian languages, UTF-16 is the scientifically superior storage format, reducing file size by \~33% compared to UTF-8.

For detailed research notes, read docs/JOURNAL.md.

## **📜 Methodology**

This benchmark adheres to strict standards to ensure validity:

* **Warm Cache I/O:** Measures the maximum throughput of the OS file cache, eliminating disk hardware variance.  
* **20MB Normalization:** Standardizes all datasets to \~20MB to balance CPU saturation with RAM safety.  
* **Zero-Overhead:** Verified via cProfile to ensure \>99% of execution time is spent in the actual encode/decode methods.

For the full defense of these methods, read docs/METHODOLOGY.md.

**Author:** Avyakths | **License:** Open Source