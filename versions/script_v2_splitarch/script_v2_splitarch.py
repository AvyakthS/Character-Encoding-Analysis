import os
import time
import csv
import psutil

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

# 4. Get our own process for monitoring
process = psutil.Process(os.getpid())

# --- Main Program ---

# We will store results in two separate lists
io_results = []
cpu_results = []

print("Running encoding analysis V2... This may take a moment.\n")

# --- Test Suite 1: File I/O (Disk-Bound) ---
print("--- Test Suite 1: File I/O (Disk-Bound) ---")
for test_name, source_file in datasets_to_test:
    
    print(f"  Testing Dataset: {test_name} ({source_file})")
    
    try:
        with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
            text_data = f.read()
    except FileNotFoundError:
        print(f"    ERROR: Source file not found: {source_file}\n")
        continue

    for encoding in encodings_map[test_name]:
        filename = f"test_output.{encoding}.txt"
        
        # Reset monitors
        process.cpu_percent(interval=None) # Reset baseline
        ram_before = process.memory_info().rss

        try:
            # --- 1. Write Performance Test ---
            start_write_time = time.perf_counter()
            for _ in range(ITERATIONS):
                with open(filename, "w", encoding=encoding, errors="ignore") as f:
                    f.write(text_data)
            end_write_time = time.perf_counter()
            write_time = (end_write_time - start_write_time) / ITERATIONS
            
            file_size = os.path.getsize(filename)
            
            # --- 2. Read Performance Test ---
            start_read_time = time.perf_counter()
            for _ in range(ITERATIONS):
                with open(filename, "r", encoding=encoding, errors="ignore") as f:
                    content = f.read()
            end_read_time = time.perf_counter()
            read_time = (end_read_time - start_read_time) / ITERATIONS
            
            # --- 3. Get System Stats for I/O Test ---
            # Note: This is CPU/RAM for *both* read and write loops combined
            cpu_load = process.cpu_percent(interval=None)
            ram_after = process.memory_info().rss
            ram_delta_mb = (ram_after - ram_before) / (1024 * 1024)
            
            io_results.append({
                "Dataset": test_name,
                "Encoding": encoding,
                "File Size (Bytes)": file_size,
                "Avg. Write Time (s)": write_time,
                "Avg. Read Time (s)": read_time,
                "Avg CPU Load (%)": cpu_load,
                "RAM Delta (MB)": ram_delta_mb
            })
            
            os.remove(filename)

        except Exception as e:
            io_results.append({
                "Dataset": test_name, "Encoding": encoding,
                "File Size (Bytes)": f"N/A (Error: {e})",
                "Avg. Write Time (s)": "N/A", "Avg. Read Time (s)": "N/A",
                "Avg CPU Load (%)": "N/A", "RAM Delta (MB)": "N/A"
            })

# --- Test Suite 2: In-Memory (CPU-Bound) ---
print("\n--- Test Suite 2: In-Memory (CPU-Bound) ---")
for test_name, source_file in datasets_to_test:
    
    print(f"  Testing Dataset: {test_name} ({source_file})")
    
    try:
        with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
            text_data = f.read()
    except FileNotFoundError:
        print(f"    ERROR: Source file not found: {source_file}\n")
        continue

    for encoding in encodings_map[test_name]:
        
        # Reset monitors
        process.cpu_percent(interval=None) # Reset baseline
        ram_before = process.memory_info().rss
        
        try:
            # --- 1. Encode Performance (CPU-Bound) ---
            start_encode_time = time.perf_counter()
            for _ in range(ITERATIONS):
                encoded_data = text_data.encode(encoding, errors="ignore")
            end_encode_time = time.perf_counter()
            avg_encode_time = (end_encode_time - start_encode_time) / ITERATIONS
            
            # We must use the 'encoded_data' from the last iteration for decode
            
            # --- 2. Decode Performance (CPU-Bound) ---
            start_decode_time = time.perf_counter()
            for _ in range(ITERATIONS):
                decoded_data = encoded_data.decode(encoding, errors="ignore")
            end_decode_time = time.perf_counter()
            avg_decode_time = (end_decode_time - start_decode_time) / ITERATIONS

            # --- 3. Get System Stats for CPU-Bound Test ---
            cpu_load = process.cpu_percent(interval=None)
            ram_after = process.memory_info().rss
            ram_delta_mb = (ram_after - ram_before) / (1024 * 1024)

            cpu_results.append({
                "Dataset": test_name,
                "Encoding": encoding,
                "Avg. Encode Time (s)": avg_encode_time,
                "Avg. Decode Time (s)": avg_decode_time,
                "Avg CPU Load (%)": cpu_load,
                "RAM Delta (MB)": ram_delta_mb
            })

        except Exception as e:
            cpu_results.append({
                "Dataset": test_name, "Encoding": encoding,
                "Avg. Encode Time (s)": f"N/A (Error: {e})",
                "Avg. Decode Time (s)": "N/A",
                "Avg CPU Load (%)": "N/A", "RAM Delta (MB)": "N/A"
            })


# --- 4. Write to CSV Log Files ---
if io_results:
    with open("io_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=io_results[0].keys())
        writer.writeheader()
        writer.writerows(io_results)
    print(f"\nSuccessfully wrote I/O test log to: io_results.csv")
    
if cpu_results:
    with open("cpu_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cpu_results[0].keys())
        writer.writeheader()
        writer.writerows(cpu_results)
    print(f"Successfully wrote CPU test log to: cpu_results.csv")

# --- 5. Print the Reports to Console ---

if io_results:
    print("\n--- FINAL RESULTS (File I/O) ---")
    headers = io_results[0].keys()
    # Dynamic formatting is complex, so let's use fixed-width for this one
    print(f"{'Dataset':<23} | {'Encoding':<10} | {'File Size (Bytes)':<18} | {'Avg. Write Time (s)':<22} | {'Avg. Read Time (s)':<22} | {'Avg CPU (%)':<15} | {'RAM Delta (MB)':<15}")
    print("-" * 135)
    for res in io_results:
        print(f"{res['Dataset']:<23} | {res['Encoding']:<10} | {str(res['File Size (Bytes)']):<18} | {res['Avg. Write Time (s)']:<22.8f} | {res['Avg. Read Time (s)']:<22.8f} | {res['Avg CPU Load (%)']:<15.2f} | {res['RAM Delta (MB)']:<15.4f}")

if cpu_results:
    print("\n--- FINAL RESULTS (In-Memory CPU) ---")
    print(f"{'Dataset':<23} | {'Encoding':<10} | {'Avg. Encode Time (s)':<22} | {'Avg. Decode Time (s)':<22} | {'Avg CPU (%)':<15} | {'RAM Delta (MB)':<15}")
    print("-" * 115)
    for res in cpu_results:
        print(f"{res['Dataset']:<23} | {res['Encoding']:<10} | {res['Avg. Encode Time (s)']:<22.8f} | {res['Avg. Decode Time (s)']:<22.8f} | {res['Avg CPU Load (%)']:<15.2f} | {res['RAM Delta (MB)']:<15.4f}")