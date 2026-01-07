# 📓 Research Journal
*A chronological record of the experiments, failures, and breakthroughs encountered during the study.*

---

## 🏁 Phase 1: The Baseline (v1 - v2)
* **Objective:** Establish basic Read/Write metrics.
* **Observation:** Initial results were erratic. Small files (1KB-10KB) processed instantly, returning `0.00s` on standard timers.
* **Correction:** We determined that a standardised, larger dataset was required to overcome the resolution limits of system timers.

---

## 🧠 Phase 2: The Memory Investigation (v3)
* **Objective:** Analyse RAM efficiency.
* **Action:** Switched from `psutil` to `tracemalloc`.
* **Discovery:** We observed a massive overhead in UTF-8 for small files. Phase 3 proved this was a fixed interpreter startup cost, not a linear scaling inefficiency, resolving the **"Small File Anomaly."**

---

## ⚡ Phase 3: The Performance Analysis (v4 - v7)
* **Objective:** Isolate CPU vs. Disk performance.
* **Action:** Decoupled I/O tests from In-Memory tests.
* **Discovery:** We isolated the **"UTF-8 CPU Tax."** Decoding UTF-32 is nearly instant (`0.002s`) compared to UTF-8 (`0.017s`) for complex text. This confirmed that fixed-width encodings allow the CPU to skip bitwise validation, offering a massive speed advantage.

---

## ⚖️ Phase 4: Standardisation (v8)
* **Objective:** Finalise comparative data.
* **Action:** Built the **Auto-Prep Suite**.
* **Outcome:** Successfully verified the **CJK Storage Theorem**, proving a **~33% reduction** in file size when using UTF-16 for Asian scripts.

---

## 📈 Phase 5: Visualization & The Memory Spike (v9)
* **Objective:** Visualisation and Optimisation.
* **Action:** Implemented `Matplotlib` charts and **Adaptive Timing**.

> **🚨 Major Discovery:** We encountered the **Multilingual Memory Spike**. Mixed-language files caused RAM usage to jump **400%** (79MB RAM for a 20MB file).
>
> **Analysis:** This confirms that Python upgrades mixed strings to a fixed-width 4-byte internal representation (UCS-4) to support `O(1)` indexing. This is a critical finding for capacity planning in multilingual applications.