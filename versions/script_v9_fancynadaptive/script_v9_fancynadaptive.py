import os
import time
import csv
import psutil
import tracemalloc
import cProfile
import pstats
import io
import sys
import glob
import re
import math
import threading
import concurrent.futures

# --- Optional Dependency: Matplotlib ---
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# --- Dynamic Path Resolution ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_freesize")
STD_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_standardized")

# --- Configuration ---
TARGET_SIZE_MB = 20
TARGET_BYTES = TARGET_SIZE_MB * 1024 * 1024
FILES_TO_IGNORE = ['analysis_report.txt', 'requirements.txt']
ENCODINGS_TO_TEST = ['ascii', 'utf-8', 'utf-16', 'utf-32']

# ADAPTIVE SETTINGS
TARGET_TEST_DURATION_SEC = 2.0  # Aim for the test to run for ~2 seconds
MIN_ITERATIONS = 100            # Hard lower limit for statistical validity

ANALYSIS_BASELINE = "utf-8"
process = psutil.Process(os.getpid())
BASE_INDENT = "  "

# --- Thread-Safe Logger ---
class Logger:
    """
    Thread-safe dual-stream logger.
    """
    def __init__(self, filename):
        try:
            self.terminal = sys.stdout
            self.file = open(filename, "w", encoding="utf-8")
            self.lock = threading.Lock()
        except Exception as e:
            print(f"FATAL: Could not open log file {filename}. Error: {e}")
            sys.exit(1)

    def log(self, message=""):
        with self.lock:
            self.terminal.write(message + "\n")
            self.file.write(message + "\n")
            self.file.flush()

    def close(self):
        self.file.close()

# --- Printing Helpers ---
def print_beautiful_header(logger, title):
    border = "═" * (len(title) + 4)
    logger.log(f"\n\n\n{BASE_INDENT}╔{border}╗")
    logger.log(f"{BASE_INDENT}║  {title.upper()}  ║")
    logger.log(f"{BASE_INDENT}╚{border}╝\n")

def print_beautiful_table(logger, title, data_rows, indent_level=2):
    indent_str = BASE_INDENT * indent_level
    if not data_rows:
        logger.log(f"{indent_str}► No data for {title}")
        return
    
    # Exclude internal keys and the 'Dataset' key (since title tells us the dataset)
    display_keys = [k for k in data_rows[0].keys() if k not in ['data_loss', 'Dataset']]
    
    formatted_rows = []
    for row in data_rows:
        new_row = {}
        for k in display_keys:
            val = row.get(k, "N/A")
            if isinstance(val, float):
                new_row[k] = f"{val:.4f}" if "MB" in k or "x" in str(val) else f"{val:.8f}"
            elif isinstance(val, int):
                new_row[k] = f"{val:,}"
            else:
                new_row[k] = str(val)
        formatted_rows.append(new_row)

    col_widths = {k: len(k) for k in display_keys}
    for row in formatted_rows:
        for k in display_keys:
            col_widths[k] = max(col_widths[k], len(row[k]))

    logger.log(f"{indent_str}► {title}\n")
    top = f"{indent_str}╔" + "╦".join(["═" * (col_widths[k] + 2) for k in display_keys]) + "╗"
    logger.log(top)
    head = f"{indent_str}║" + "║".join([f" {k.ljust(col_widths[k])} " for k in display_keys]) + "║"
    logger.log(head)
    sep = f"{indent_str}╠" + "╬".join(["═" * (col_widths[k] + 2) for k in display_keys]) + "╣"
    logger.log(sep)
    for row in formatted_rows:
        line = f"{indent_str}║" + "║".join([f" {row[k].ljust(col_widths[k])} " for k in display_keys]) + "║"
        logger.log(line)
    bot = f"{indent_str}╚" + "╩".join(["═" * (col_widths[k] + 2) for k in display_keys]) + "╝"
    logger.log(bot)
    logger.log("\n")

def print_beautiful_box(logger, title, content, indent_level=2):
    indent_str = BASE_INDENT * indent_level
    lines = content.strip().split('\n')
    width = max(max(len(line) for line in lines if line), len(title))
    logger.log(f"{indent_str}╔═[ {title} ]{'═' * (width - len(title) - 1)}╗")
    for line in lines:
        logger.log(f"{indent_str}║ {line.ljust(width)} ║")
    logger.log(f"{indent_str}╚{'═' * (width + 2)}╝\n")

# --- Dataset Auto-Prep Logic ---
def get_intent(filename):
    name = filename.lower()
    if "english" in name or "ascii" in name: return "ASCII"
    if "cjk" in name or "chinese" in name: return "CJK"
    if "emoji" in name: return "EMOJI"
    return "GENERIC"

def purify_text(text, intent):
    if intent == "ASCII": return text.encode('ascii', 'ignore').decode('ascii')
    if intent == "CJK": return "".join(re.findall(r'[\u4e00-\u9fff]+', text))
    if intent == "EMOJI": 
        return "".join([line.split('#')[1].strip().split(' ')[0] 
                        for line in text.split('\n') if '#' in line and ';' in line])
    return text

def prepare_single_dataset(src, logger):
    """Worker function for parallel processing."""
    base_name = os.path.basename(src)
    bench_name_only = base_name.replace(".txt", "_bench.txt")
    bench_full_path = os.path.join(STD_FILES_DIR, bench_name_only)
    
    if os.path.exists(bench_full_path):
        logger.log(f"{BASE_INDENT}  ✓ [Cached] {bench_name_only}")
        return bench_full_path

    try:
        intent = get_intent(src)
        with open(src, "r", encoding="utf-8", errors="ignore") as f: raw = f.read()
        
        clean = purify_text(raw, intent)
        if not clean: 
            logger.log(f"{BASE_INDENT}  ! [Skipped] {base_name} (Empty after purification)")
            return None
        
        curr_len = len(clean.encode('utf-8'))
        if curr_len == 0: return None
        
        mult = int(TARGET_BYTES / curr_len) + 1
        final_content = clean * mult
        
        with open(bench_full_path, "w", encoding="utf-8") as f: f.write(final_content)
        
        final_size = os.path.getsize(bench_full_path)
        logger.log(f"{BASE_INDENT}  ✓ [Generated] {bench_name_only} ({final_size/1024/1024:.2f} MB)")
        return bench_full_path
    except Exception as e:
        logger.log(f"{BASE_INDENT}  ! [Error] {base_name}: {e}")
        return None

def prepare_datasets(logger):
    """
    Parallelized dataset preparation.
    """
    all_files = glob.glob(os.path.join(USER_FILES_DIR, "*.txt"))
    source_files = [f for f in all_files if f not in FILES_TO_IGNORE and "_bench.txt" not in f]
    
    logger.log("--- Phase 1: Parallel Dataset Preparation ---")
    logger.log(f"{BASE_INDENT}• Input Directory: {USER_FILES_DIR}")
    logger.log(f"{BASE_INDENT}• Target Size: {TARGET_SIZE_MB} MB")
    
    generated = []
    # Using ThreadPoolExecutor because operations are I/O mixed with light String ops
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(prepare_single_dataset, src, logger): src for src in source_files}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                generated.append(result)

    logger.log(f"\n{BASE_INDENT}► Ready to benchmark {len(generated)} standardized files.\n")
    return generated

# --- Visualization Logic ---
def generate_charts(io_data, cpu_data, logger):
    if not MATPLOTLIB_AVAILABLE:
        logger.log(f"{BASE_INDENT}! Matplotlib not found. Skipping chart generation.")
        return

    logger.log("--- Phase 3: Generating Visualizations ---")
    datasets = sorted(list(set(d['Dataset'] for d in io_data)))
    encodings = ENCODINGS_TO_TEST
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'] 
    
    # 1. Storage Size
    try:
        plt.figure(figsize=(10, 6))
        x = range(len(datasets))
        width = 0.2
        for i, enc in enumerate(encodings):
            y_vals = []
            for ds in datasets:
                row = next((r for r in io_data if r['Dataset'] == ds and r['Encoding'] == enc), None)
                if row and isinstance(row.get('File Size'), int):
                    y_vals.append(row['File Size'] / (1024*1024))
                else:
                    y_vals.append(0)
            plt.bar([p + width*i for p in x], y_vals, width, label=enc, color=colors[i], alpha=0.8)

        plt.xlabel('Datasets'); plt.ylabel('File Size (MB)')
        plt.title('Storage Efficiency: Encoding Impact on File Size')
        plt.xticks([p + width*1.5 for p in x], datasets, rotation=15)
        plt.legend(); plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "chart_storage_efficiency.png")); plt.close()
        logger.log(f"{BASE_INDENT}✓ Saved Chart: chart_storage_efficiency.png")
    except Exception as e: logger.log(f"{BASE_INDENT}! Error generating Storage Chart: {e}")

    # 2. CPU Decode Speed
    try:
        plt.figure(figsize=(10, 6))
        x = range(len(datasets))
        width = 0.2
        for i, enc in enumerate(encodings):
            y_vals = []
            for ds in datasets:
                row = next((r for r in cpu_data if r['Dataset'] == ds and r['Encoding'] == enc), None)
                if row and isinstance(row.get('Avg Decode (s)'), float):
                    y_vals.append(row['Avg Decode (s)'] * 1000)
                else:
                    y_vals.append(0)
            plt.bar([p + width*i for p in x], y_vals, width, label=enc, color=colors[i], alpha=0.8)

        plt.xlabel('Datasets'); plt.ylabel('Avg Decode Time (ms)')
        plt.title('The CPU Tax: Decoding Speed by Encoding')
        plt.xticks([p + width*1.5 for p in x], datasets, rotation=15)
        plt.legend(); plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "chart_cpu_decode_speed.png")); plt.close()
        logger.log(f"{BASE_INDENT}✓ Saved Chart: chart_cpu_decode_speed.png")
    except Exception as e: logger.log(f"{BASE_INDENT}! Error generating CPU Chart: {e}")

    # 3. Peak Memory
    try:
        plt.figure(figsize=(10, 6))
        x = range(len(datasets))
        width = 0.2
        for i, enc in enumerate(encodings):
            y_vals = []
            for ds in datasets:
                row = next((r for r in cpu_data if r['Dataset'] == ds and r['Encoding'] == enc), None)
                if row and isinstance(row.get('Peak Enc (MB)'), float):
                    y_vals.append(row['Peak Enc (MB)'])
                else:
                    y_vals.append(0)
            plt.bar([p + width*i for p in x], y_vals, width, label=enc, color=colors[i], alpha=0.8)

        plt.xlabel('Datasets'); plt.ylabel('Peak RAM Usage (MB)')
        plt.title('Memory Footprint: Peak Allocation during Encoding')
        plt.xticks([p + width*1.5 for p in x], datasets, rotation=15)
        plt.legend(); plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(); plt.savefig(os.path.join(SCRIPT_DIR, "chart_memory_usage.png")); plt.close()
        logger.log(f"{BASE_INDENT}✓ Saved Chart: chart_memory_usage.png")
    except Exception as e: logger.log(f"{BASE_INDENT}! Error generating Memory Chart: {e}")
    logger.log("")

# --- Adaptive Benchmarking Logic ---

def run_adaptive_loop(op_func, *args):
    """
    Executes op_func(*args) repeatedly.
    1. Runs MIN_ITERATIONS.
    2. Calculates pace.
    3. Extends run until total time >= TARGET_TEST_DURATION_SEC.
    Returns: (avg_time_per_op, total_iterations, total_time)
    """
    # 1. Warm-up / Min Phase
    start_min = time.perf_counter()
    for _ in range(MIN_ITERATIONS):
        op_func(*args)
    duration_min = time.perf_counter() - start_min
    
    # 2. Check and Extend
    if duration_min < TARGET_TEST_DURATION_SEC:
        avg_pace = duration_min / MIN_ITERATIONS
        # Avoid div by zero if extremely fast
        if avg_pace == 0: avg_pace = 0.000000001
        
        estimated_needed = int((TARGET_TEST_DURATION_SEC - duration_min) / avg_pace)
        # Cap excessive iterations if operation is basically instant (to prevent billion-loop hangs)
        if estimated_needed > 10_000_000: estimated_needed = 10_000_000
        
        for _ in range(estimated_needed):
            op_func(*args)
            
        total_iters = MIN_ITERATIONS + estimated_needed
        total_time = time.perf_counter() - start_min
    else:
        total_iters = MIN_ITERATIONS
        total_time = duration_min
        
    return (total_time / total_iters), total_iters, total_time

def run_io_test(test_name, text_data, encoding):
    filename = f"test_output.{encoding}.txt"
    process.cpu_percent(interval=None) 
    ram_before = process.memory_info().rss
    
    try:
        # Wrapper closures for adaptive loop
        def _write_op():
            with open(filename, "w", encoding=encoding, errors="ignore") as f: f.write(text_data)
            
        def _read_op():
            with open(filename, "r", encoding=encoding, errors="ignore") as f: _ = f.read()

        # Run Adaptive Tests
        avg_w, n_w, t_w = run_adaptive_loop(_write_op)
        
        # Get actual file size after writing
        f_size = os.path.getsize(filename)
        
        avg_r, n_r, t_r = run_adaptive_loop(_read_op)
        
        cpu = process.cpu_percent(interval=None)
        ram_delta = (process.memory_info().rss - ram_before) / (1024 * 1024)
        if os.path.exists(filename): os.remove(filename)
        
        return {
            "Dataset": test_name, "Encoding": encoding, "File Size": f_size,
            "Avg Write (s)": avg_w, "Avg Read (s)": avg_r, 
            "CPU (%)": cpu, "RAM Delta (MB)": ram_delta,
            "meta_iters_w": n_w, "meta_time_w": t_w,
            "meta_iters_r": n_r, "meta_time_r": t_r
        }
    except Exception as e:
        if os.path.exists(filename): os.remove(filename)
        return {"Dataset": test_name, "Encoding": encoding, "File Size": 0, "Error": str(e)}

def run_cpu_test(test_name, text_data, encoding):
    try:
        process.cpu_percent(interval=None)
        
        # Pre-calculate encoded bytes for the decode test
        encoded_data = text_data.encode(encoding, errors="ignore")
        
        def _enc_op():
            _ = text_data.encode(encoding, errors="ignore")
            
        def _dec_op():
            _ = encoded_data.decode(encoding, errors="ignore")
            
        # Run Adaptive Tests
        avg_e, n_e, t_e = run_adaptive_loop(_enc_op)
        avg_d, n_d, t_d = run_adaptive_loop(_dec_op)
        
        cpu = process.cpu_percent(interval=None)
        
        # Memory Tracing (Single Pass)
        tracemalloc.start()
        _ = text_data.encode(encoding, errors="ignore")
        _, peak_e = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Note: We don't trace decode memory separately as encode is usually the peak alloc
        peak_d = peak_e # Placeholder or implement separate trace if needed
        
        return {
            "Dataset": test_name, "Encoding": encoding, 
            "Avg Encode (s)": avg_e, "Avg Decode (s)": avg_d,
            "CPU (%)": cpu, "Peak Enc (MB)": peak_e/(1024**2), "Peak Dec (MB)": peak_d/(1024**2),
            "meta_iters_e": n_e, "meta_time_e": t_e,
            "meta_iters_d": n_d, "meta_time_d": t_d
        }
    except Exception as e:
         return {"Dataset": test_name, "Encoding": encoding, "Error": str(e)}

def run_profiler(text_data, encoding):
    pr = cProfile.Profile()
    pr.enable()
    # Profile fixed iterations (e.g. 100) just to validate overhead
    for _ in range(100):
        d = text_data.encode(encoding, errors="ignore")
        _ = d.decode(encoding, errors="ignore")
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(5, 'encode')
    ps.print_stats(5, 'decode')
    return s.getvalue()

def analyze(io_data, cpu_data):
    io_final, cpu_final = [], []
    datasets = sorted(list(set(d['Dataset'] for d in io_data)))
    
    for ds in datasets:
        ds_io = [r for r in io_data if r['Dataset'] == ds]
        base_io = next((r for r in ds_io if r['Encoding'] == ANALYSIS_BASELINE), None)
        
        for r in ds_io:
            if not base_io or 'Error' in r: continue
            # FIX: We now PRESERVE the 'Dataset' key here so we can filter by it later
            row = {k: v for k, v in r.items() if not k.startswith('meta_')}
            row['Size vs Base'] = f"{(r['File Size'] / base_io['File Size'] * 100):.1f}%" if base_io['File Size'] > 0 else "N/A"
            if r.get('data_loss'): row['File Size'] = f"{row['File Size']:,} (Loss!)"
            io_final.append(row)

        ds_cpu = [r for r in cpu_data if r['Dataset'] == ds]
        base_cpu = next((r for r in ds_cpu if r['Encoding'] == ANALYSIS_BASELINE), None)
        
        for r in ds_cpu:
            if not base_cpu or 'Error' in r: continue
            # FIX: Preserve 'Dataset' here too
            row = {k: v for k, v in r.items() if not k.startswith('meta_')}
            row['Enc vs Base'] = f"{base_cpu['Avg Encode (s)'] / r['Avg Encode (s)']:.2f}x" if r['Avg Encode (s)'] > 0 else "0.00x"
            row['Dec vs Base'] = f"{base_cpu['Avg Decode (s)'] / r['Avg Decode (s)']:.2f}x" if r['Avg Decode (s)'] > 0 else "0.00x"
            row['Mem vs Base'] = f"{(r['Peak Enc (MB)'] / base_cpu['Peak Enc (MB)'] * 100):.1f}%" if base_cpu['Peak Enc (MB)'] > 0 else "N/A"
            cpu_final.append(row)
            
    return io_final, cpu_final

# --- Main ---
def main():
    logger = Logger("analysis_report.txt")
    print_beautiful_header(logger, "Encoding Benchmark Suite v9.0 (Fancy Edition)")
    logger.log(f"{BASE_INDENT}• Mode: Adaptive")
    logger.log(f"{BASE_INDENT}• Target Duration: {TARGET_TEST_DURATION_SEC}s per test")
    logger.log(f"{BASE_INDENT}• Hard Min Iterations: {MIN_ITERATIONS}")
    
    # 1. Prepare
    datasets = prepare_datasets(logger)
    
    if not datasets: 
        logger.log(f"\n{BASE_INDENT}ERROR: No datasets found or generated.")
        logger.close()
        return
    
    io_res, cpu_res, prof_res = [], [], {}
    
    # 2. Execute
    logger.log("--- Phase 2: Adaptive Benchmarking Execution ---")
    for ds_path in datasets:
        ds_name = os.path.basename(ds_path)
        print_beautiful_header(logger, f"Testing: {ds_name}")
        
        try:
            with open(ds_path, "r", encoding="utf-8", errors="ignore") as f: text = f.read()
            is_ascii = text.isascii()
            logger.log(f"{BASE_INDENT}✓ Loaded {len(text):,} chars")
        except: continue
            
        # I/O TESTS
        logger.log(f"\n{BASE_INDENT}► Running Disk I/O Tests...")
        for enc in ENCODINGS_TO_TEST:
            logger.log(f"{BASE_INDENT*2}• {enc}...", ) 
            r_io = run_io_test(ds_name, text, enc)
            
            if 'Error' not in r_io:
                loss_tag = " (Loss!)" if (enc == 'ascii' and not is_ascii) else ""
                # Log adaptive stats
                logger.log(f"{BASE_INDENT*3}├─ Write: {r_io['Avg Write (s)']:.4f}s [n={r_io['meta_iters_w']:,} | {r_io['meta_time_w']:.2f}s]")
                logger.log(f"{BASE_INDENT*3}├─ Read:  {r_io['Avg Read (s)']:.4f}s [n={r_io['meta_iters_r']:,} | {r_io['meta_time_r']:.2f}s]")
                logger.log(f"{BASE_INDENT*3}└─ Size:  {r_io['File Size']/1024/1024:.2f} MB{loss_tag}")
            else:
                logger.log(f"{BASE_INDENT*3}└─ Failed: {r_io['Error']}")

            if enc == 'ascii' and not is_ascii: r_io['data_loss'] = True
            io_res.append(r_io)
            
        # CPU TESTS
        logger.log(f"\n{BASE_INDENT}► Running In-Memory Tests...")
        for enc in ENCODINGS_TO_TEST:
            logger.log(f"{BASE_INDENT*2}• {enc}...", )
            r_cpu = run_cpu_test(ds_name, text, enc)
            
            if 'Error' not in r_cpu:
                 logger.log(f"{BASE_INDENT*3}├─ Encode: {r_cpu['Avg Encode (s)']:.4f}s [n={r_cpu['meta_iters_e']:,} | {r_cpu['meta_time_e']:.2f}s]")
                 logger.log(f"{BASE_INDENT*3}├─ Decode: {r_cpu['Avg Decode (s)']:.4f}s [n={r_cpu['meta_iters_d']:,} | {r_cpu['meta_time_d']:.2f}s]")
                 logger.log(f"{BASE_INDENT*3}└─ RAM:    {r_cpu['Peak Enc (MB)']:.2f} MB")

            if enc == 'ascii' and not is_ascii: r_cpu['data_loss'] = True
            cpu_res.append(r_cpu)
            
        # Profiler (First valid run only)
        if not prof_res:
            logger.log(f"\n{BASE_INDENT}► Running cProfile Verification...")
            prof_res[ds_name] = run_profiler(text, "utf-8")
            logger.log(f"{BASE_INDENT*2}✓ Captured profiling data")

    # 3. Analyze & Report
    final_io, final_cpu = analyze(io_res, cpu_res)
    
    # 4. Generate Visuals
    generate_charts(io_res, cpu_res, logger)
    
    # Save Raw CSVs
    if io_res:
        with open("io_results.csv", "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=io_res[0].keys()).writeheader(); csv.DictWriter(f, fieldnames=io_res[0].keys()).writerows(io_res)
    if cpu_res:
        with open("cpu_results.csv", "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=cpu_res[0].keys()).writeheader(); csv.DictWriter(f, fieldnames=cpu_res[0].keys()).writerows(cpu_res)

    # Print Clean Report
    print_beautiful_header(logger, "FINAL ANALYSIS REPORT")
    
    unique_names = sorted(list(set(r['Dataset'] for r in io_res)))
    for ds_name in unique_names:
        # ROBUST FILTERING: Now strictly matching by Dataset Name
        rows_io = [r for r in final_io if r['Dataset'] == ds_name]
        rows_cpu = [r for r in final_cpu if r['Dataset'] == ds_name]

        if rows_io: print_beautiful_table(logger, f"{ds_name} - Storage & I/O", rows_io)
        if rows_cpu: print_beautiful_table(logger, f"{ds_name} - CPU & Memory", rows_cpu)

    logger.close()
    print("\n[+] Benchmark Complete. Report saved to 'analysis_report.txt'")
    if MATPLOTLIB_AVAILABLE:
        print("[+] Charts saved to script directory (chart_*.png)")

if __name__ == "__main__":
    main()