import os
import time
import csv
import psutil
import tracemalloc
import cProfile
import pstats
import io

# --- Dynamic Path Resolution ---
# 1. Get the directory where THIS script is located (e.g., /versions/script_v1_prototype/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Define the User Input Directory (Go up 2 levels: versions -> root -> freesize...)
USER_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_freesize")

# 3. Define the Standardized Directory (Go up 2 levels -> standardized...)
STD_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_standardized")

# --- Configuration ---
datasets_to_test = [
    ("English (ASCII-heavy)", os.path.join(USER_FILES_DIR, "english.txt")),
    ("Multilingual", os.path.join(USER_FILES_DIR, "multilingual.txt"))
]

encodings_map = {
    "English (ASCII-heavy)": ["ascii", "utf-8", "utf-16", "utf-32"],
    "Multilingual": ["utf-8", "utf-16", "utf-32"]
}

ITERATIONS = 1000
ANALYSIS_BASELINE = "utf-8"
process = psutil.Process(os.getpid())

# --- Core Logic Functions (Identical to v4) ---

# --- Test 1: File I/O (Disk-Bound) ---
def run_io_test(test_name, text_data, encoding):
    filename = f"test_output.{encoding}.txt"
    process.cpu_percent(interval=None) 
    ram_before = process.memory_info().rss
    try:
        start_write_time = time.perf_counter()
        for _ in range(ITERATIONS):
            with open(filename, "w", encoding=encoding, errors="ignore") as f:
                f.write(text_data)
        end_write_time = time.perf_counter()
        write_time = (end_write_time - start_write_time) / ITERATIONS
        file_size = os.path.getsize(filename)
        start_read_time = time.perf_counter()
        for _ in range(ITERATIONS):
            with open(filename, "r", encoding=encoding, errors="ignore") as f:
                content = f.read()
        end_read_time = time.perf_counter()
        read_time = (end_read_time - start_read_time) / ITERATIONS
        cpu_load = process.cpu_percent(interval=None)
        ram_after = process.memory_info().rss
        ram_delta_mb = (ram_after - ram_before) / (1024 * 1024)
        os.remove(filename)
        return {
            "Dataset": test_name, "Encoding": encoding,
            "File Size (Bytes)": file_size,
            "Avg. Write Time (s)": write_time,
            "Avg. Read Time (s)": read_time,
            "Avg CPU Load (%)": cpu_load,
            "RAM Delta (MB)": ram_delta_mb
        }
    except Exception as e:
        return {
            "Dataset": test_name, "Encoding": encoding,
            "File Size (Bytes)": f"N/A (Error: {e})", "Avg. Write Time (s)": "N/A",
            "Avg. Read Time (s)": "N/A", "Avg CPU Load (%)": "N/A", "RAM Delta (MB)": "N/A"
        }

# --- Test 2: In-Memory (CPU-Bound) - V4 METHODOLOGY ---
def run_cpu_test(test_name, text_data, encoding):
    try:
        # --- 2a. Timing Test (Pure Speed) ---
        process.cpu_percent(interval=None)
        start_encode_time = time.perf_counter()
        for _ in range(ITERATIONS):
            encoded_data = text_data.encode(encoding, errors="ignore")
        end_encode_time = time.perf_counter()
        avg_encode_time = (end_encode_time - start_encode_time) / ITERATIONS
        start_decode_time = time.perf_counter()
        for _ in range(ITERATIONS):
            decoded_data = encoded_data.decode(encoding, errors="ignore")
        end_decode_time = time.perf_counter()
        avg_decode_time = (end_decode_time - start_decode_time) / ITERATIONS
        cpu_load = process.cpu_percent(interval=None)
        # --- 2b. Memory Test (Pure Cost) ---
        tracemalloc.start()
        encoded_data_single = text_data.encode(encoding, errors="ignore")
        _, encode_mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        tracemalloc.clear_traces()
        tracemalloc.start()
        decoded_data_single = encoded_data_single.decode(encoding, errors="ignore")
        _, decode_mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        tracemalloc.clear_traces()
        return {
            "Dataset": test_name, "Encoding": encoding,
            "Avg. Encode Time (s)": avg_encode_time,
            "Avg. Decode Time (s)": avg_decode_time,
            "Avg CPU Load (%)": cpu_load,
            "Encode Peak (MB)": encode_mem_peak / (1024 * 1024),
            "Decode Peak (MB)": decode_mem_peak / (1024 * 1024)
        }
    except Exception as e:
        tracemalloc.stop()
        tracemalloc.clear_traces()
        return {
            "Dataset": test_name, "Encoding": encoding,
            "Avg. Encode Time (s)": f"N/A (Error: {e})", "Avg. Decode Time (s)": "N/A",
            "Avg CPU Load (%)": "N/A", "Encode Peak (MB)": "N/A", "Decode Peak (MB)": "N/A"
        }

# --- Test 3: Profiler Validation ---
def run_profiler_test(text_data, encoding):
    """Runs cProfile on the encode/decode loops and returns a string."""
    pr = cProfile.Profile()
    pr.enable()
    # --- Run the code to be profiled ---
    for _ in range(ITERATIONS):
        encoded_data = text_data.encode(encoding, errors="ignore")
    for _ in range(ITERATIONS):
        decoded_data = encoded_data.decode(encoding, errors="ignore")
    # --- End of profiled code ---
    pr.disable()
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(5, 'encode')
    ps.print_stats(5, 'decode')
    return s.getvalue()

# --- Test 4: Final Analysis ---
def run_analysis(io_results, cpu_results):
    analysis_results = []
    for row in io_results:
        baseline_io = next((r for r in io_results if r['Dataset'] == row['Dataset'] and r['Encoding'] == ANALYSIS_BASELINE), None)
        if not baseline_io or not isinstance(row['File Size (Bytes)'], int):
            continue 
        baseline_size = baseline_io['File Size (Bytes)']
        analysis_results.append({
            "Test": "File I/O", "Dataset": row['Dataset'], "Encoding": row['Encoding'],
            "Metric": "File Size", "Value": f"{row['File Size (Bytes)']:,} B",
            "vs. Baseline": f"{(row['File Size (Bytes)'] / baseline_size * 100):.1f}%"
        })
    for row in cpu_results:
        baseline_cpu = next((r for r in cpu_results if r['Dataset'] == row['Dataset'] and r['Encoding'] == ANALYSIS_BASELINE), None)
        if not baseline_cpu or not isinstance(row['Avg. Encode Time (s)'], float):
            continue
        baseline_encode_time = baseline_cpu['Avg. Encode Time (s)']
        baseline_decode_time = baseline_cpu['Avg. Decode Time (s)']
        baseline_encode_mem = baseline_cpu['Encode Peak (MB)']
        encode_speedup = baseline_encode_time / row['Avg. Encode Time (s)'] if row['Avg. Encode Time (s)'] > 0 else 0
        decode_speedup = baseline_decode_time / row['Avg. Decode Time (s)'] if row['Avg. Decode Time (s)'] > 0 else 0
        analysis_results.append({
            "Test": "In-Memory", "Dataset": row['Dataset'], "Encoding": row['Encoding'],
            "Metric": "Encode Time", "Value": f"{row['Avg. Encode Time (s)']:.8f} s",
            "vs. Baseline": f"{encode_speedup:.2f}x"
        })
        analysis_results.append({
            "Test": "In-Memory", "Dataset": row['Dataset'], "Encoding": row['Encoding'],
            "Metric": "Decode Time", "Value": f"{row['Avg. Decode Time (s)']:.8f} s",
            "vs. Baseline": f"{decode_speedup:.2f}x"
        })
        analysis_results.append({
            "Test": "In-Memory", "Dataset": row['Dataset'], "Encoding": row['Encoding'],
            "Metric": "Encode Peak Mem", "Value": f"{row['Encode Peak (MB)']:.4f} MB",
            "vs. Baseline": f"{(row['Encode Peak (MB)'] / baseline_encode_mem * 100):.1f}%"
        })
        analysis_results.append({
            "Test": "In-Memory", "Dataset": row['Dataset'], "Encoding": row['Encoding'],
            "Metric": "Decode Peak Mem", "Value": f"{row['Decode Peak (MB)']:.4f} MB",
            "vs. Baseline": "N/A" # No baseline for this one
        })
    return analysis_results

# --- NEW V5 PRINTING FUNCTIONS ---

def print_beautiful_header(title):
    """Prints a decorative header."""
    border = "═" * (len(title) + 4)
    print(f"\n\n\n{' ' * 4}╔{border}╗")
    print(f"{' ' * 4}║{' ' * (len(title) + 4)}║")
    print(f"{' ' * 4}║  {title.upper()}  ║")
    print(f"{' ' * 4}║{' ' * (len(title) + 4)}║")
    print(f"{' ' * 4}╚{border}╝\n")

def print_beautiful_table(title, data_rows):
    """Prints a list of dictionaries in a beautiful box-drawing table."""
    
    if not data_rows:
        print(f"  No data for {title}")
        return

    headers = data_rows[0].keys()
    
    # --- 1. Format all data and get column widths ---
    formatted_rows = []
    for row in data_rows:
        formatted_row = {}
        for col, val in row.items():
            if isinstance(val, float):
                # Standard formatting for floats
                formatted_row[col] = f"{val:.6f}"
            elif isinstance(val, int):
                # Add commas to large integers
                formatted_row[col] = f"{val:,}"
            else:
                formatted_row[col] = str(val)
        formatted_rows.append(formatted_row)

    # Calculate max width for each column
    col_widths = {h: len(h) for h in headers}
    for row in formatted_rows:
        for h, val in row.items():
            if len(val) > col_widths[h]:
                col_widths[h] = len(val)

    # --- 2. Print the table ---
    print(f"  ► {title}\n")
    
    # Top border
    top_border = "  ╔"
    for i, h in enumerate(headers):
        top_border += "═" * (col_widths[h] + 2)
        top_border += "╦" if i < len(headers) - 1 else "╗"
    print(top_border)
    
    # Header row
    header_row = "  ║"
    for h in headers:
        header_row += f" {h.ljust(col_widths[h])} ║"
    print(header_row)
    
    # Middle border
    middle_border = "  ╠"
    for i, h in enumerate(headers):
        middle_border += "═" * (col_widths[h] + 2)
        middle_border += "╬" if i < len(headers) - 1 else "╣"
    print(middle_border)

    # Data rows
    for row in formatted_rows:
        data_row_str = "  ║"
        for h in headers:
            data_row_str += f" {row[h].ljust(col_widths[h])} ║"
        print(data_row_str)
        
    # Bottom border
    bottom_border = "  ╚"
    for i, h in enumerate(headers):
        bottom_border += "═" * (col_widths[h] + 2)
        bottom_border += "╩" if i < len(headers) - 1 else "╝"
    print(bottom_border)
    print("\n")

# --- Main Execution ---
def main():
    io_results_list = []
    cpu_results_list = []
    profiler_reports = {} # Store profiler text
    
    unique_datasets = [name for name, _ in datasets_to_test]

    for test_name, source_file in datasets_to_test:
        print_beautiful_header(f"Loading Dataset: {test_name} ({source_file})")
        try:
            with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
                text_data = f.read()
            print(f"  Successfully loaded {len(text_data):,} characters.")
        except FileNotFoundError:
            print(f"    ERROR: Source file not found: {source_file}\n")
            continue
        
        print(f"  Running Test Suite 1: File I/O (Disk-Bound)...")
        for encoding in encodings_map[test_name]:
            io_results_list.append(run_io_test(test_name, text_data, encoding))
            
        print(f"  Running Test Suite 2: In-Memory (CPU-Bound)...")
        for encoding in encodings_map[test_name]:
            cpu_results_list.append(run_cpu_test(test_name, text_data, encoding))
            
        if test_name == "English (ASCII-heavy)": # Only run profiler on one
            print(f"  Running Test Suite 3: cProfile Validation (on utf-8)...")
            profiler_reports['utf-8'] = run_profiler_test(text_data, "utf-8")
    
    # --- All Data Collected. Now, Write CSVs ---
    if io_results_list:
        with open("io_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=io_results_list[0].keys())
            writer.writeheader()
            writer.writerows(io_results_list)
        print(f"\n  ✓ Successfully wrote raw I/O test log to: io_results.csv")
        
    if cpu_results_list:
        with open("cpu_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cpu_results_list[0].keys())
            writer.writeheader()
            writer.writerows(cpu_results_list)
        print(f"  ✓ Successfully wrote raw CPU test log to: cpu_results.csv")
        
    # --- Run Analysis and Write Report CSV ---
    analysis_report = run_analysis(io_results_list, cpu_results_list)
    if analysis_report:
        with open("analysis_report.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=analysis_report[0].keys())
            writer.writeheader()
            writer.writerows(analysis_report)
        print(f"  ✓ Successfully wrote final analysis log to: analysis_report.csv")

    # --- NEW V5 CONSOLE REPORTING ---
    
    # --- Print Raw Data Tables ---
    print_beautiful_header("Test 1: File I/O (Disk-Bound) - Raw Data")
    for dataset in unique_datasets:
        # *** FIX IS HERE ***
        # Create a *new list* of *new dictionaries* that omits the 'Dataset' key
        # This prevents modifying our original io_results_list
        rows = [{k: v for k, v in r.items() if k != 'Dataset'}
                for r in io_results_list if r['Dataset'] == dataset]
        print_beautiful_table(f"Dataset: {dataset}", rows)

    print_beautiful_header("Test 2: In-Memory (CPU-Bound) - Raw Data")
    for dataset in unique_datasets:
        # *** FIX IS HERE ***
        rows = [{k: v for k, v in r.items() if k != 'Dataset'}
                for r in cpu_results_list if r['Dataset'] == dataset]
        print_beautiful_table(f"Dataset: {dataset}", rows)

    # --- Print Profiler Report ---
    print_beautiful_header("Test 3: cProfile Validation")
    if profiler_reports:
        print(f"  ► Profiler Report for: utf-8 (English Dataset)\n")
        print(profiler_reports['utf-8'])
    else:
        print("  No profiler reports were run.")

    # --- Print Analysis Report ---
    print_beautiful_header("Test 4: Final Analysis Report (vs. Baseline)")
    for test_type in ["File I/O", "In-Memory"]:
        print(f"\n  --- Analysis for: {test_type} ---")
        for dataset in unique_datasets:
            # *** FIX IS HERE ***
            rows = [{k: v for k, v in r.items() if k not in ['Test', 'Dataset']}
                    for r in analysis_report if r['Test'] == test_type and r['Dataset'] == dataset]
            if not rows: continue # Skip if no data
            print_beautiful_table(f"Dataset: {dataset}", rows)

if __name__ == "__main__":
    main()