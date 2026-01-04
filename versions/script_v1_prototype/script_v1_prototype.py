import os
import time
import csv

# --- Dynamic Path Resolution ---
# 1. Get the directory where THIS script is located (e.g., /versions/script_v1_prototype/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Define the User Input Directory (Go up 2 levels: versions -> root -> freesize...)
USER_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_freesize")

# 3. Define the Standardized Directory (Go up 2 levels -> standardized...)
STD_FILES_DIR = os.path.join(SCRIPT_DIR, "..", "..", "user_bench_files_standardized")

# --- Configuration ---

# 1. Define the datasets to test
#    (Test Name, Source File)
datasets_to_test = [
    ("English (ASCII-heavy)", os.path.join(USER_FILES_DIR, "english.txt")),
    ("Multilingual", os.path.join(USER_FILES_DIR, "multilingual.txt"))
]

# 2. Define the encodings for each test
#    The English text will be used to test all four
#    The Multilingual text can only be tested with Unicode encodings
encodings_map = {
    "English (ASCII-heavy)": ["ascii", "utf-8", "utf-16", "utf-32"],
    "Multilingual": ["utf-8", "utf-16", "utf-32"]
}

# 3. Performance test settings
ITERATIONS = 1000  # Loop for stable read/write averaging
output_csv_file = "encoding_results.csv"

# --- Main Program ---

# List to hold all our dictionary results
all_results = []

print("Running encoding analysis... This may take a moment.\n")

# Loop through our two source files
for test_name, source_file in datasets_to_test:
    
    print(f"--- Testing Dataset: {test_name} ({source_file}) ---")
    
    # First, read the source file's content
    try:
        #
        # --- THIS IS THE FIX ---
        # Added 'errors="ignore"' to skip any invalid bytes
        # in the source test file.
        #
        with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
            text_data = f.read()
            
    except FileNotFoundError:
        print(f"  ERROR: Source file not found: {source_file}")
        print("  Please download it and place it in the same folder as the script.\n")
        continue
    except Exception as e:
        print(f"  ERROR reading {source_file}: {e}\n")
        continue

    # Now, test this content against its list of encodings
    for encoding in encodings_map[test_name]:
        filename = f"test_output.{encoding}.txt"
        
        # --- 1. Write Performance Test ---
        start_write_time = time.perf_counter()
        try:
            # Use 'errors="ignore"' for the ASCII test to drop non-ASCII chars
            with open(filename, "w", encoding=encoding, errors="ignore") as f:
                f.write(text_data)
            end_write_time = time.perf_counter()
            write_time = (end_write_time - start_write_time) / ITERATIONS
            
            # --- 2. Get File Size ---
            file_size = os.path.getsize(filename)
            
            # --- 3. Read Performance Test ---
            start_read_time = time.perf_counter()
            for _ in range(ITERATIONS):
                with open(filename, "r", encoding=encoding, errors="ignore") as f:
                    content = f.read()
            end_read_time = time.perf_counter()
            read_time = (end_read_time - start_read_time) / ITERATIONS
            
            # Store results
            all_results.append({
                "Dataset": test_name,
                "Encoding": encoding,
                "File Size (Bytes)": file_size,
                "Avg. Write Time (s)": write_time,
                "Avg. Read Time (s)": read_time
            })
            
            # Clean up the test file
            os.remove(filename)

        except Exception as e:
            all_results.append({
                "Dataset": test_name,
                "Encoding": encoding,
                "File Size (Bytes)": f"N/A (Error: {e})",
                "Avg. Write Time (s)": "N/A",
                "Avg. Read Time (s)": "N/A"
            })

# --- 4. Write to CSV Log File ---
if all_results:
    # Get the headers from the keys of the first result
    headers = all_results[0].keys()
    
    with open(output_csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"\nSuccessfully wrote detailed log to: {output_csv_file}")
else:
    print("\nNo results to write to log file.")

# --- 5. Print the Report to Console ---
print("\n--- FINAL RESULTS (Console) ---")
print(f"{'Dataset':<23} | {'Encoding':<10} | {'File Size (Bytes)':<18} | {'Avg. Write Time (s)':<22} | {'Avg. Read Time (s)':<22}")
print("-" * 105)

for res in all_results:
    # Format numbers for printing, handling potential N/A strings
    try:
        f_size = f"{res['File Size (Bytes)']:,}" # Add commas
    except (ValueError, TypeError):
        f_size = str(res['File Size (Bytes)'])
        
    try:
        w_time = f"{res['Avg. Write Time (s)']:<22.8f}"
    except (ValueError, TypeError):
        w_time = f"{res['Avg. Write Time (s)']:<22}"
        
    try:
        r_time = f"{res['Avg. Read Time (s)']:<22.8f}"
    except (ValueError, TypeError):
        r_time = f"{res['Avg. Read Time (s)']:<22}"

    print(f"{res['Dataset']:<23} | {res['Encoding']:<10} | {f_size:<18} | {w_time} | {r_time}")