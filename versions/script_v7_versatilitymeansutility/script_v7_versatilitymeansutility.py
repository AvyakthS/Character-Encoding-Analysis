import os
import time
import csv
import psutil
import tracemalloc
import cProfile
import pstats
import io
import sys
import glob # <-- NEW IMPORT

# --- Dynamic Path Resolution ---
# 1. Get the directory where THIS script is located (e.g., /versions/script_v1_prototype/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Define the User Input Directory (Go up 2 levels: versions -> root -> freesize...)
USER_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_freesize")

# 3. Define the Standardized Directory (Go up 2 levels -> standardized...)
STD_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_standardized")

# --- Configuration ---
# V8: No more hardcoded lists!
# We will auto-detect all .txt files.

# V8: Files to ignore during auto-detection.
FILES_TO_IGNORE = [
    'analysis_report.txt', # Our own log file
]
# We don't need to add .csv files as we're only globbing for .txt
ENCODINGS_TO_TEST = ['ascii', 'utf-8', 'utf-16', 'utf-32']

ITERATIONS = 1000
ANALYSIS_BASELINE = "utf-8"
process = psutil.Process(os.getpid())

# Base indent for all console output
BASE_INDENT = "  "

# --- NEW V7 LOGGER CLASS ---
class Logger:
    """Mirrors print() calls to both the console and a log file."""
    def __init__(self, filename):
        try:
            self.terminal = sys.stdout
            self.file = open(filename, "w", encoding="utf-8")
        except Exception as e:
            print(f"FATAL: Could not open log file {filename}. Error: {e}")
            sys.exit(1)

    def log(self, message=""):
        """Prints a message to the console and writes it to the log file."""
        self.terminal.write(message + "\n")
        self.file.write(message + "\n")
        self.file.flush() # Ensure it writes immediately

    def close(self):
        """Closes the log file."""
        self.file.close()

# --- Core Logic Functions (Unchanged) ---

# --- Test 1: File I/O (Disk-Bound) ---
def run_io_test(test_name, text_data, encoding):
    # 'test_name' is now just the filename, e.g. "english.txt"
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

# --- Test 2: In-Memory (CPU-Bound) ---
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
    for _ in range(ITERATIONS):
        encoded_data = text_data.encode(encoding, errors="ignore")
    for _ in range(ITERATIONS):
        decoded_data = encoded_data.decode(encoding, errors="ignore")
    pr.disable()
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(5, 'encode')
    ps.print_stats(5, 'decode')
    return s.getvalue()

# --- Test 4: Final Analysis (V8 REWORK) ---
def run_analysis(io_results, cpu_results):
    """Reworked to build clean, un-pivoted tables and check for data_loss flag."""
    io_analysis_results = []
    cpu_analysis_results = []
    
    unique_datasets = list(set([r['Dataset'] for r in io_results]))
    unique_datasets.sort() # Ensure consistent order

    for dataset in unique_datasets:
        # --- Process I/O Data ---
        io_rows = [r for r in io_results if r['Dataset'] == dataset]
        baseline_io = next((r for r in io_rows if r['Encoding'] == ANALYSIS_BASELINE and isinstance(r['File Size (Bytes)'], int)), None)
        
        for row in io_rows:
            if not baseline_io or not isinstance(row['File Size (Bytes)'], int):
                continue
            
            # V8: Add the (Data Loss!) warning flag
            file_size_val = f"{row['File Size (Bytes)']:,} B"
            if row.get('data_loss', False): # Check for our new flag
                file_size_val += " (Data Loss!)"
                
            io_analysis_results.append({
                "Dataset": dataset,
                "Encoding": row['Encoding'],
                "File Size": file_size_val, # Changed key for clarity
                "Size (vs. Base)": f"{(row['File Size (Bytes)'] / baseline_io['File Size (Bytes)'] * 100):.1f}%"
            })
            
        # --- Process CPU Data ---
        cpu_rows = [r for r in cpu_results if r['Dataset'] == dataset]
        baseline_cpu = next((r for r in cpu_rows if r['Encoding'] == ANALYSIS_BASELINE and isinstance(r['Avg. Encode Time (s)'], float)), None)
        
        for row in cpu_rows:
            if not baseline_cpu or not isinstance(row['Avg. Encode Time (s)'], float):
                continue

            encode_speedup = baseline_cpu['Avg. Encode Time (s)'] / row['Avg. Encode Time (s)'] if row['Avg. Encode Time (s)'] > 0 else 0
            decode_speedup = baseline_cpu['Avg. Decode Time (s)'] / row['Avg. Decode Time (s)'] if row['Avg. Decode Time (s)'] > 0 else 0
            
            encode_mem_vs_base = "N/A"
            if baseline_cpu['Encode Peak (MB)'] > 0:
                 encode_mem_vs_base = f"{(row['Encode Peak (MB)'] / baseline_cpu['Encode Peak (MB)'] * 100):.1f}%"
            
            cpu_analysis_results.append({
                "Dataset": dataset,
                "Encoding": row['Encoding'],
                "Encode Time (s)": row['Avg. Encode Time (s)'],
                "Encode (vs. Base)": f"{encode_speedup:.2f}x",
                "Decode Time (s)": row['Avg. Decode Time (s)'],
                "Decode (vs. Base)": f"{decode_speedup:.2f}x",
                "Encode Peak (MB)": row['Encode Peak (MB)'],
                "Encode Mem (vs. Base)": encode_mem_vs_base,
                "Decode Peak (MB)": row['Decode Peak (MB)'],
            })

    return io_analysis_results, cpu_analysis_results

# --- V7 PRINTING FUNCTIONS (Take logger) ---

def print_beautiful_header(logger, title):
    """Prints a decorative header with indentation."""
    border = "═" * (len(title) + 4)
    logger.log(f"\n\n\n{BASE_INDENT}╔{border}╗")
    logger.log(f"{BASE_INDENT}║{' ' * (len(title) + 4)}║")
    logger.log(f"{BASE_INDENT}║  {title.upper()}  ║")
    logger.log(f"{BASE_INDENT}║{' ' * (len(title) + 4)}║")
    logger.log(f"{BASE_INDENT}╚{border}╝\n")

def print_beautiful_table(logger, title, data_rows, indent_level=2):
    """Prints a list of dictionaries in a beautiful box-drawing table."""
    
    indent_str = BASE_INDENT * indent_level
    
    if not data_rows:
        logger.log(f"{indent_str}► No data for {title}")
        return

    # V8: Handle 'data_loss' key, but don't print it
    headers = [h for h in data_rows[0].keys() if h != 'data_loss']
    
    # --- 1. Format all data and get column widths ---
    formatted_rows = []
    for row in data_rows:
        formatted_row = {}
        for col, val in row.items():
            if col == 'data_loss': continue # Skip this key
            
            if isinstance(val, float):
                if "Time" in col:
                    formatted_row[col] = f"{val:.8f}" # More precision for time
                else:
                    formatted_row[col] = f"{val:.4f}" # Standard for MB
            elif isinstance(val, int):
                formatted_row[col] = f"{val:,}" # Add commas
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
    logger.log(f"{indent_str}► {title}\n")
    
    # Top border
    top_border = f"{indent_str}╔"
    for i, h in enumerate(headers):
        top_border += "═" * (col_widths[h] + 2)
        top_border += "╦" if i < len(headers) - 1 else "╗"
    logger.log(top_border)
    
    # Header row
    header_row = f"{indent_str}║"
    for h in headers:
        header_row += f" {h.ljust(col_widths[h])} ║"
    logger.log(header_row)
    
    # Middle border
    middle_border = f"{indent_str}╠"
    for i, h in enumerate(headers):
        middle_border += "═" * (col_widths[h] + 2)
        middle_border += "╬" if i < len(headers) - 1 else "╣"
    logger.log(middle_border)

    # Data rows
    for row in formatted_rows:
        data_row_str = f"{indent_str}║"
        for h in headers:
            data_row_str += f" {row[h].ljust(col_widths[h])} ║"
        logger.log(data_row_str)
        
    # Bottom border
    bottom_border = f"{indent_str}╚"
    for i, h in enumerate(headers):
        bottom_border += "═" * (col_widths[h] + 2)
        bottom_border += "╩" if i < len(headers) - 1 else "╝"
    logger.log(bottom_border)
    logger.log("\n")

def print_beautiful_box(logger, title, content, indent_level=2):
    """Prints a string of content inside a decorative box."""
    indent_str = BASE_INDENT * indent_level
    content_lines = content.strip().split('\n')
    max_width = 0
    for line in content_lines:
        if len(line) > max_width:
            max_width = len(line)
    max_width = max(max_width, len(title)) # Ensure box is wide enough for title

    # Top border
    logger.log(f"{indent_str}╔═[ {title} ]{'═' * (max_width - len(title) - 1)}╗")

    # Content lines
    for line in content_lines:
        logger.log(f"{indent_str}║ {line.ljust(max_width)} ║")
        
    # Bottom border
    logger.log(f"{indent_str}╚{'═' * (max_width + 2)}╝\n")

# --- Main Execution (V8 REWORK) ---
def main():
    logger = Logger("analysis_report.txt")
    
    io_results_list = []
    cpu_results_list = []
    profiler_reports = {} 
    
    # --- V8: Auto-detect datasets ---
    logger.log("--- Auto-Detecting Datasets ---")
    all_txt_files = glob.glob(os.path.join(USER_FILES_DIR, "*.txt"))
    datasets_to_run = [f for f in all_txt_files if f not in FILES_TO_IGNORE]
    
    if not datasets_to_run:
        logger.log(f"{BASE_INDENT}ERROR: No dataset '.txt' files found in this directory.")
        logger.log(f"{BASE_INDENT}Please add files like 'english.txt' to run the benchmark.")
        logger.close()
        return

    logger.log(f"{BASE_INDENT}✓ Found {len(datasets_to_run)} dataset(s): {', '.join(datasets_to_run)}\n")
    datasets_to_run.sort() # Ensure consistent order
    
    # --- Run main test loop ---
    for source_file in datasets_to_run:
        test_name = os.path.basename(source_file) # Returns just "english.txt"
        
        print_beautiful_header(logger, f"Loading Dataset: {test_name}")
        try:
            file_size_bytes = os.path.getsize(source_file)
            with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
                text_data = f.read()
            
            # --- V8: "Smart" ASCII Check ---
            is_pure_ascii = text_data.isascii()
            
            logger.log(f"{BASE_INDENT * 2}✓ Successfully loaded {len(text_data):,} characters ({file_size_bytes:,} bytes).")
            if is_pure_ascii:
                logger.log(f"{BASE_INDENT * 2}► File is 100% ASCII-compatible.")
            else:
                logger.log(f"{BASE_INDENT * 2}► File contains non-ASCII characters.")
                
        except FileNotFoundError:
            logger.log(f"{BASE_INDENT * 2}ERROR: Source file not found: {source_file}\n")
            continue
        except Exception as e:
            logger.log(f"{BASE_INDENT * 2}ERROR: Could not read file {source_file}: {e}\n")
            continue
        
        # --- Run Tests ---
        logger.log(f"\n{BASE_INDENT * 2}Running Test Suite 1: File I/O (Disk-Bound)...")
        for encoding in ENCODINGS_TO_TEST:
            io_result = run_io_test(test_name, text_data, encoding)
            if encoding == 'ascii' and not is_pure_ascii:
                io_result['data_loss'] = True # Add the warning flag
            io_results_list.append(io_result)
            
        logger.log(f"{BASE_INDENT * 2}Running Test Suite 2: In-Memory (CPU-Bound)...")
        for encoding in ENCODINGS_TO_TEST:
            cpu_result = run_cpu_test(test_name, text_data, encoding)
            if encoding == 'ascii' and not is_pure_ascii:
                cpu_result['data_loss'] = True # Add flag here too (though it's not used)
            cpu_results_list.append(cpu_result)
            
        # Run profiler only on the *first* detected dataset (to save time)
        if source_file == datasets_to_run[0]: 
            logger.log(f"{BASE_INDENT * 2}Running Test Suite 3: cProfile Validation (on utf-8)...")
            profiler_reports[source_file] = run_profiler_test(text_data, "utf-8")
    
    # --- Write CSVs ---
    if io_results_list:
        with open("io_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=io_results_list[0].keys())
            writer.writeheader()
            writer.writerows(io_results_list)
        logger.log(f"\n{BASE_INDENT}✓ Successfully wrote raw I/O test log to: io_results.csv")
        
    if cpu_results_list:
        with open("cpu_results.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cpu_results_list[0].keys())
            writer.writeheader()
            writer.writerows(cpu_results_list)
        logger.log(f"{BASE_INDENT}✓ Successfully wrote raw CPU test log to: cpu_results.csv")
    
    # --- Run Analysis ---
    io_analysis, cpu_analysis = run_analysis(io_results_list, cpu_results_list)

    # --- Print Reports ---
    
    # 1. Extract the unique dataset names actually found in the results to ensure valid matching
    executed_datasets = sorted(list(set(r['Dataset'] for r in io_results_list)))

    print_beautiful_header(logger, "Test 1: File I/O (Disk-Bound) - Raw Data")
    for dataset in executed_datasets:
        rows = [{k: v for k, v in r.items() if k != 'Dataset'}
                for r in io_results_list if r['Dataset'] == dataset]
        if rows: print_beautiful_table(logger, f"Dataset: {dataset}", rows)

    print_beautiful_header(logger, "Test 2: In-Memory (CPU-Bound) - Raw Data")
    for dataset in executed_datasets:
        rows = [{k: v for k, v in r.items() if k != 'Dataset'}
                for r in cpu_results_list if r['Dataset'] == dataset]
        if rows: print_beautiful_table(logger, f"Dataset: {dataset}", rows)

    print_beautiful_header(logger, "Test 3: cProfile Validation")
    if profiler_reports:
        for dataset, report in profiler_reports.items():
            print_beautiful_box(logger, f"Profiler Report for: utf-8 ({os.path.basename(dataset)})", report)
    else:
        logger.log(f"{BASE_INDENT * 2}► No profiler reports were run.")

    print_beautiful_header(logger, "Test 4: Final Analysis Report (vs. Baseline)")
    for dataset in executed_datasets:
        io_rows = [{k:v for k,v in r.items() if k != 'Dataset'} for r in io_analysis if r['Dataset'] == dataset]
        if io_rows:
            print_beautiful_table(logger, f"Dataset: {dataset} - File I/O Analysis", io_rows)
            
        cpu_rows = [{k:v for k,v in r.items() if k != 'Dataset'} for r in cpu_analysis if r['Dataset'] == dataset]
        if cpu_rows:
            print_beautiful_table(logger, f"Dataset: {dataset} - In-Memory CPU Analysis", cpu_rows)

    logger.close()
    print(f"\n[+] Analysis complete. Full report saved to 'analysis_report.txt'")

if __name__ == "__main__":
    main()