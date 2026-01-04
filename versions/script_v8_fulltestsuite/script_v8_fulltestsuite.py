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

# --- Dynamic Path Resolution ---
# 1. Get the directory where THIS script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Define the User Input Directory (freesize)
USER_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_freesize")

# 3. Define the Standardized Directory (standardized)
STD_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_standardized")

# --- Configuration ---
TARGET_SIZE_MB = 20
TARGET_BYTES = TARGET_SIZE_MB * 1024 * 1024
FILES_TO_IGNORE = ['analysis_report.txt', 'requirements.txt']
ENCODINGS_TO_TEST = ['ascii', 'utf-8', 'utf-16', 'utf-32']
ITERATIONS = 1000
ANALYSIS_BASELINE = "utf-8"
process = psutil.Process(os.getpid())
BASE_INDENT = "  "

# --- Logger Class ---
class Logger:
    def __init__(self, filename):
        try:
            self.terminal = sys.stdout
            self.file = open(filename, "w", encoding="utf-8")
        except Exception as e:
            print(f"FATAL: Could not open log file {filename}. Error: {e}")
            sys.exit(1)
    def log(self, message=""):
        self.terminal.write(message + "\n")
        self.file.write(message + "\n")
        self.file.flush()
    def close(self):
        self.file.close()

# --- Dynamic Table Printing ---
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
    
    # Filter out internal keys like 'data_loss' for display
    display_keys = [k for k in data_rows[0].keys() if k != 'data_loss']
    
    # Pre-format values to strings to calculate width
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

    # Dynamic Column Width Calculation
    col_widths = {k: len(k) for k in display_keys}
    for row in formatted_rows:
        for k in display_keys:
            col_widths[k] = max(col_widths[k], len(row[k]))

    # Print Table
    logger.log(f"{indent_str}► {title}\n")
    
    # Top Border
    top = f"{indent_str}╔" + "╦".join(["═" * (col_widths[k] + 2) for k in display_keys]) + "╗"
    logger.log(top)
    
    # Headers
    head = f"{indent_str}║" + "║".join([f" {k.ljust(col_widths[k])} " for k in display_keys]) + "║"
    logger.log(head)
    
    # Separator
    sep = f"{indent_str}╠" + "╬".join(["═" * (col_widths[k] + 2) for k in display_keys]) + "╣"
    logger.log(sep)
    
    # Data
    for row in formatted_rows:
        line = f"{indent_str}║" + "║".join([f" {row[k].ljust(col_widths[k])} " for k in display_keys]) + "║"
        logger.log(line)
        
    # Bottom Border
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
        # Simple extraction of likely emoji lines from standard files
        return "".join([line.split('#')[1].strip().split(' ')[0] 
                        for line in text.split('\n') if '#' in line and ';' in line])
    return text

def prepare_datasets(logger):
    # Search in USER_FILES_DIR (Freesize)
    all_files = glob.glob(os.path.join(USER_FILES_DIR, "*.txt"))
    source_files = [f for f in all_files if f not in FILES_TO_IGNORE and "_bench.txt" not in f]
    
    generated = []
    logger.log("--- Checking Datasets ---")
    
    for src in source_files:
        base_name = os.path.basename(src)
        bench_name_only = base_name.replace(".txt", "_bench.txt")
        # Save to STD_FILES_DIR (Standardized)
        bench_full_path = os.path.join(STD_FILES_DIR, bench_name_only)
        
        # Smart Cache Check
        if os.path.exists(bench_full_path):
            generated.append(bench_full_path)
            continue # Skip if already exists
            
        # Generation Logic
        intent = get_intent(src)
        try:
            with open(src, "r", encoding="utf-8", errors="ignore") as f: raw = f.read()
            clean = purify_text(raw, intent)
            if not clean: continue
            
            # Multiply
            curr_len = len(clean.encode('utf-8'))
            if curr_len == 0: continue
            
            mult = int(TARGET_BYTES / curr_len) + 1
            final_content = clean * mult
            
            with open(bench_full_path, "w", encoding="utf-8") as f: f.write(final_content)
            generated.append(bench_full_path)
            logger.log(f"{BASE_INDENT}✓ Generated {bench_name_only} (Standardized to ~{TARGET_SIZE_MB}MB)")
            
        except Exception as e:
            logger.log(f"{BASE_INDENT}! Error preparing {base_name}: {e}")

    logger.log(f"{BASE_INDENT}► Ready to benchmark {len(generated)} standardized files.\n")
    return generated

# --- Benchmarking Logic ---
def run_io_test(test_name, text_data, encoding):
    filename = f"test_output.{encoding}.txt"
    process.cpu_percent(interval=None) 
    ram_before = process.memory_info().rss
    try:
        start_w = time.perf_counter()
        for _ in range(ITERATIONS):
            with open(filename, "w", encoding=encoding, errors="ignore") as f: f.write(text_data)
        avg_w = (time.perf_counter() - start_w) / ITERATIONS
        
        f_size = os.path.getsize(filename)
        
        start_r = time.perf_counter()
        for _ in range(ITERATIONS):
            with open(filename, "r", encoding=encoding, errors="ignore") as f: _ = f.read()
        avg_r = (time.perf_counter() - start_r) / ITERATIONS
        
        cpu = process.cpu_percent(interval=None)
        ram_delta = (process.memory_info().rss - ram_before) / (1024 * 1024)
        os.remove(filename)
        
        return {"Dataset": test_name, "Encoding": encoding, "File Size": f_size,
                "Avg Write (s)": avg_w, "Avg Read (s)": avg_r, "CPU (%)": cpu, "RAM Delta (MB)": ram_delta}
    except Exception as e:
        return {"Dataset": test_name, "Encoding": encoding, "File Size": 0, "Error": str(e)}

def run_cpu_test(test_name, text_data, encoding):
    try:
        process.cpu_percent(interval=None)
        start_e = time.perf_counter()
        for _ in range(ITERATIONS): encoded = text_data.encode(encoding, errors="ignore")
        avg_e = (time.perf_counter() - start_e) / ITERATIONS
        
        start_d = time.perf_counter()
        for _ in range(ITERATIONS): _ = encoded.decode(encoding, errors="ignore")
        avg_d = (time.perf_counter() - start_d) / ITERATIONS
        
        cpu = process.cpu_percent(interval=None)
        
        tracemalloc.start()
        _ = text_data.encode(encoding, errors="ignore")
        _, peak_e = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        tracemalloc.start()
        _ = encoded.decode(encoding, errors="ignore")
        _, peak_d = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {"Dataset": test_name, "Encoding": encoding, "Avg Encode (s)": avg_e, "Avg Decode (s)": avg_d,
                "CPU (%)": cpu, "Peak Enc (MB)": peak_e/(1024**2), "Peak Dec (MB)": peak_d/(1024**2)}
    except Exception as e:
         return {"Dataset": test_name, "Encoding": encoding, "Error": str(e)}

def run_profiler(text_data, encoding):
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(ITERATIONS):
        d = text_data.encode(encoding, errors="ignore")
    for _ in range(ITERATIONS):
        _ = d.decode(encoding, errors="ignore")
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(5, 'encode')
    ps.print_stats(5, 'decode')
    return s.getvalue()

def analyze(io_data, cpu_data):
    io_final, cpu_final = [], []
    # Identify unique datasets from the collected results
    datasets = sorted(list(set(d['Dataset'] for d in io_data)))
    
    for ds in datasets:
        # I/O Analysis
        ds_io = [r for r in io_data if r['Dataset'] == ds]
        base_io = next((r for r in ds_io if r['Encoding'] == ANALYSIS_BASELINE), None)
        
        for r in ds_io:
            if not base_io or 'Error' in r: continue
            row = {k: v for k, v in r.items() if k != 'Dataset'}
            row['Size vs Base'] = f"{(r['File Size'] / base_io['File Size'] * 100):.1f}%" if base_io['File Size'] > 0 else "N/A"
            if r.get('data_loss'): row['File Size'] = f"{row['File Size']:,} (Loss!)"
            io_final.append(row)

        # CPU Analysis
        ds_cpu = [r for r in cpu_data if r['Dataset'] == ds]
        base_cpu = next((r for r in ds_cpu if r['Encoding'] == ANALYSIS_BASELINE), None)
        
        for r in ds_cpu:
            if not base_cpu or 'Error' in r: continue
            row = {k: v for k, v in r.items() if k != 'Dataset'}
            row['Enc vs Base'] = f"{base_cpu['Avg Encode (s)'] / r['Avg Encode (s)']:.2f}x" if r['Avg Encode (s)'] > 0 else "0.00x"
            row['Dec vs Base'] = f"{base_cpu['Avg Decode (s)'] / r['Avg Decode (s)']:.2f}x" if r['Avg Decode (s)'] > 0 else "0.00x"
            row['Mem vs Base'] = f"{(r['Peak Enc (MB)'] / base_cpu['Peak Enc (MB)'] * 100):.1f}%" if base_cpu['Peak Enc (MB)'] > 0 else "N/A"
            cpu_final.append(row)
            
    return io_final, cpu_final

# --- Main ---
def main():
    logger = Logger("analysis_report.txt")
    print_beautiful_header(logger, "Encoding Benchmark Suite v8.0")
    
    # 1. Prepare
    # (Will look in USER_FILES_DIR and save to STD_FILES_DIR)
    datasets = prepare_datasets(logger)
    
    if not datasets: 
        logger.log(f"\n{BASE_INDENT}ERROR: No datasets found or generated.")
        logger.log(f"{BASE_INDENT}Please ensure .txt files are in: {os.path.abspath(USER_FILES_DIR)}")
        logger.close()
        return
    
    io_res, cpu_res, prof_res = [], [], {}
    
    # 2. Execute
    for ds_path in datasets:
        ds_name = os.path.basename(ds_path)
        logger.log(f"► Benchmarking: {ds_name}")
        
        try:
            with open(ds_path, "r", encoding="utf-8", errors="ignore") as f: text = f.read()
            is_ascii = text.isascii()
        except: continue
            
        for enc in ENCODINGS_TO_TEST:
            # Run IO
            r_io = run_io_test(ds_name, text, enc)
            if enc == 'ascii' and not is_ascii: r_io['data_loss'] = True
            io_res.append(r_io)
            
            # Run CPU
            r_cpu = run_cpu_test(ds_name, text, enc)
            if enc == 'ascii' and not is_ascii: r_cpu['data_loss'] = True
            cpu_res.append(r_cpu)
            
        # Profiler (First valid run only)
        if not prof_res:
            prof_res[ds_name] = run_profiler(text, "utf-8")

    # 3. Analyze & Report
    final_io, final_cpu = analyze(io_res, cpu_res)
    
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
        # Correctly filter final analysis results by dataset name
        rows_io = [r for i, r in enumerate(final_io) if io_res[i]['Dataset'] == ds_name]
        rows_cpu = [r for i, r in enumerate(final_cpu) if cpu_res[i]['Dataset'] == ds_name]

        if rows_io: print_beautiful_table(logger, f"{ds_name} - Storage & I/O", rows_io)
        if rows_cpu: print_beautiful_table(logger, f"{ds_name} - CPU & Memory", rows_cpu)

    if prof_res:
        print_beautiful_header(logger, "VALIDATION")
        for k, v in prof_res.items(): print_beautiful_box(logger, f"Profiler: {k}", v)

    logger.close()
    print("\n[+] Benchmark Complete. Report saved to 'analysis_report.txt'")

if __name__ == "__main__":
    main()
