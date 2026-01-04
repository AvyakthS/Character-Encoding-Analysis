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

# 1. Define the datasets to test
datasets_to_test = [
    ("English (ASCII-heavy)", os.path.join(USER_FILES_DIR, "english.txt")),
    ("Multilingual", os.path.join(USER_FILES_DIR, "multilingual.txt"))
]

# 2. Define the encodings for each test
encodings_map = {
    "English (ASCII-heavy)": ["ascii", "utf-8", "utf-16", "utf-32"],
    "Multilingual": ["utf-8", "utf-16", "utf-32"]
}

# 3. Performance test settings
ITERATIONS = 1000  # Loop for stable averaging
ANALYSIS_BASELINE = "utf-8" # Baseline for our analysis report

# 4. Get our own process for monitoring
process = psutil.Process(os.getpid())

# --- Test 1: File I/O (Disk-Bound) ---
def run_io_test(test_name, text_data, encoding):
    filename = f"test_output.{encoding}.txt"
    
    # Reset monitors
    process.cpu_percent(interval=None) # Reset baseline
    ram_before = process.memory_info().rss
    
    try:
        # --- 1a. Write Performance Test ---
        start_write_time = time.perf_counter()
        for _ in range(ITERATIONS):
            with open(filename, "w", encoding=encoding, errors="ignore") as f:
                f.write(text_data)
        end_write_time = time.perf_counter()
        write_time = (end_write_time - start_write_time) / ITERATIONS
        
        file_size = os.path.getsize(filename)
        
        # --- 1b. Read Performance Test ---
        start_read_time = time.perf_counter()
        for _ in range(ITERATIONS):
            with open(filename, "r", encoding=encoding, errors="ignore") as f:
                content = f.read()
        end_read_time = time.perf_counter()
        read_time = (end_read_time - start_read_time) / ITERATIONS
        
        # --- 1c. Get System Stats for I/O Test ---
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
        # Run loop *without* tracemalloc to get unpolluted time
        process.cpu_percent(interval=None) # Reset CPU
        
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
        # Run a *single* operation with tracemalloc to get exact peak memory
        
        tracemalloc.start()
        encoded_data_single = text_data.encode(encoding, errors="ignore")
        _, encode_mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        tracemalloc.clear_traces()
        # We must use the 'encoded_data_single' for a valid decode
        
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
    """Runs cProfile on the encode/decode loops and prints a summary."""
    print(f"\n--- cProfile Validation for: {encoding} ---")
    
    # Create a profiler object
    pr = cProfile.Profile()
    pr.enable()
    
    # --- Run the code to be profiled ---
    for _ in range(ITERATIONS):
        encoded_data = text_data.encode(encoding, errors="ignore")
    for _ in range(ITERATIONS):
        decoded_data = encoded_data.decode(encoding, errors="ignore")
    # --- End of profiled code ---
    
    pr.disable()
    
    # Create a string stream to catch the profiler output
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    
    # Filter output to only show top 5 lines, focused on {built-in method}
    ps.print_stats(5, 'encode')
    ps.print_stats(5, 'decode')
    
    print(s.getvalue())

# --- Test 4: Final Analysis ---
def run_analysis(io_results, cpu_results):
    """Calculates and prints a final analysis report."""
    analysis_results = []
    
    # Get baseline data (e.g., from 'English' dataset)
    # This is a bit complex, so we'll just analyze all rows
    
    for row in io_results:
        # Find the baseline row for this dataset (e.g., utf-8)
        baseline_io = next((r for r in io_results if r['Dataset'] == row['Dataset'] and r['Encoding'] == ANALYSIS_BASELINE), None)
        
        if not baseline_io or not isinstance(row['File Size (Bytes)'], int):
            continue # Skip if baseline not found or row is an error
            
        baseline_size = baseline_io['File Size (Bytes)']
        
        analysis_results.append({
            "Test": "File I/O",
            "Dataset": row['Dataset'],
            "Encoding": row['Encoding'],
            "Metric": "File Size",
            "Value": row['File Size (Bytes)'],
            "vs. Baseline": f"{(row['File Size (Bytes)'] / baseline_size * 100):.1f}%"
        })

    for row in cpu_results:
        baseline_cpu = next((r for r in cpu_results if r['Dataset'] == row['Dataset'] and r['Encoding'] == ANALYSIS_BASELINE), None)

        if not baseline_cpu or not isinstance(row['Avg. Encode Time (s)'], float):
            continue

        baseline_encode_time = baseline_cpu['Avg. Encode Time (s)']
        baseline_decode_time = baseline_cpu['Avg. Decode Time (s)']
        baseline_encode_mem = baseline_cpu['Encode Peak (MB)']

        # Calculate speedup (X times faster/slower)
        # Handle divide by zero, though unlikely
        encode_speedup = baseline_encode_time / row['Avg. Encode Time (s)'] if row['Avg. Encode Time (s)'] > 0 else 0
        decode_speedup = baseline_decode_time / row['Avg. Decode Time (s)'] if row['Avg. Decode Time (s)'] > 0 else 0
        
        analysis_results.append({
            "Test": "In-Memory",
            "Dataset": row['Dataset'],
            "Encoding": row['Encoding'],
            "Metric": "Encode Time",
            "Value": f"{row['Avg. Encode Time (s)']:.8f} s",
            "vs. Baseline": f"{encode_speedup:.2f}x"
        })
        analysis_results.append({
            "Test": "In-Memory",
            "Dataset": row['Dataset'],
            "Encoding": row['Encoding'],
            "Metric": "Decode Time",
            "Value": f"{row['Avg. Decode Time (s)']:.8f} s",
            "vs. Baseline": f"{decode_speedup:.2f}x"
        })
        analysis_results.append({
            "Test": "In-Memory",
            "Dataset": row['Dataset'],
            "Encoding": row['Encoding'],
            "Metric": "Encode Peak Mem",
            "Value": f"{row['Encode Peak (MB)']:.4f} MB",
            "vs. Baseline": f"{(row['Encode Peak (MB)'] / baseline_encode_mem * 100):.1f}%"
        })
    
    return analysis_results

# --- Main Execution ---
def main():
    io_results_list = []
    cpu_results_list = []

    for test_name, source_file in datasets_to_test:
        print(f"\n--- Loading Dataset: {test_name} ({source_file}) ---")
        try:
            with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
                text_data = f.read()
        except FileNotFoundError:
            print(f"    ERROR: Source file not found: {source_file}\n")
            continue
        
        print("  Running Test Suite 1: File I/O (Disk-Bound)...")
        for encoding in encodings_map[test_name]:
            io_results_list.append(run_io_test(test_name, text_data, encoding))
            
        print("  Running Test Suite 2: In-Memory (CPU-Bound)...")
        for encoding in encodings_map[test_name]:
            cpu_results_list.append(run_cpu_test(test_name, text_data, encoding))
            
        # Run profiler only on the large English dataset for one encoding
        if test_name == "English (ASCII-heavy)":
            print("  Running Test Suite 3: cProfile Validation (on utf-8)...")
            run_profiler_test(text_data, "utf-8")

    # --- Write Raw Data to CSVs ---
    if io_results_list:
        with open("io_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=io_results_list[0].keys())
            writer.writeheader()
            writer.writerows(io_results_list)
        print(f"\nSuccessfully wrote I/O test log to: io_results.csv")
        
    if cpu_results_list:
        with open("cpu_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cpu_results_list[0].keys())
            writer.writeheader()
            writer.writerows(cpu_results_list)
        print(f"Successfully wrote CPU test log to: cpu_results.csv")
        
    # --- Run Analysis and Print Report ---
    print("\n--- Test 4: Final Analysis Report (vs. utf-8) ---")
    analysis_report = run_analysis(io_results_list, cpu_results_list)
    
    if analysis_report:
        # Print to console
        headers = analysis_report[0].keys()
        print(f"{'Test':<11} | {'Dataset':<23} | {'Encoding':<10} | {'Metric':<18} | {'Value':<22} | {'vs. Baseline':<15}")
        print("-" * 105)
        for res in analysis_report:
            print(f"{res['Test']:<11} | {res['Dataset']:<23} | {res['Encoding']:<10} | {res['Metric']:<18} | {str(res['Value']):<22} | {res['vs. Baseline']:<15}")
        
        # Write to CSV
        with open("analysis_report.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(analysis_report)
        print(f"\nSuccessfully wrote final analysis log to: analysis_report.csv")

if __name__ == "__main__":
    main()