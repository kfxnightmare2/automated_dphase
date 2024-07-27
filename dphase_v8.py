import sys
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException

def parse_fasta(file_path):
    sequences = []
    current_sequence = {"header": "", "sequence": ""}
    
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            
            if line.startswith(">"):
                if current_sequence["header"] != "":
                    sequences.append(current_sequence)
                    current_sequence = {"header": "", "sequence": ""}
                
                current_sequence["header"] = line[1:]
            else:
                current_sequence["sequence"] += line
    
    if current_sequence["header"] != "":
        sequences.append(current_sequence)
    
    return sequences

def calculate_time_remaining(start_time, current_step, total_steps):
    elapsed_time = time.time() - start_time
    time_per_step = elapsed_time / current_step if current_step > 0 else 0
    remaining_steps = total_steps - current_step
    time_remaining = time_per_step * remaining_steps
    return time_remaining

if len(sys.argv) < 2:
    print("Usage: python script_name.py fasta_file_path")
    sys.exit(1)

fasta_file_path = sys.argv[1]
output_file_name = input("Enter the output file name (without extension): ") + ".csv"
error_output_file_name = output_file_name.replace(".csv", "_ERROR.csv")

driver = webdriver.Chrome()
driver.get("https://deephase.ch.cam.ac.uk/")

try:
    with open(output_file_name, "w", newline="") as output_file, open(error_output_file_name, "w", newline="") as error_file:
        writer = csv.writer(output_file)
        error_writer = csv.writer(error_file)
        
        writer.writerow(["RepID", "Prediction Score"])
        error_writer.writerow(["Sequence Number", "Error Reason"])
        
        textarea = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "mat-input-0"))
        )

        fasta_sequences = parse_fasta(fasta_file_path)
        
        total_steps = len(fasta_sequences)
        start_time = time.time()
        
        for i, seq in enumerate(fasta_sequences, start=1):
            amino_acid_sequence = seq["sequence"].replace("\n", "")
            
            if i > 1:
                textarea.clear()
            
            textarea.send_keys(amino_acid_sequence)
            
            WebDriverWait(driver, 20).until(
                EC.text_to_be_present_in_element_value((By.ID, "mat-input-0"), amino_acid_sequence)
            )
            
            try:
                predict_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Predict')]"))
                )
            except TimeoutException:
                error_reason = f"Predict button not found or not clickable for sequence {i}."
                print(error_reason)
                error_writer.writerow([i, error_reason])
                continue
            
            try:
                predict_button.click()
            except (ElementNotInteractableException, StaleElementReferenceException) as e:
                error_reason = f"Error clicking the predict button for sequence {i}: {e}"
                print(error_reason)
                error_writer.writerow([i, error_reason])
                continue
            
            try:
                prediction_element = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'Yes')] | //p[contains(text(), 'No')]"))
                )
                prediction_score_text = prediction_element.text
                prediction_score = prediction_score_text.split("(")[-1].split(")")[0]
            except TimeoutException:
                error_reason = f"Prediction for sequence {i} timed out."
                print(error_reason)
                error_writer.writerow([i, error_reason])
                continue
            except NoSuchElementException:
                error_reason = f"Prediction score not found for sequence {i}."
                print(error_reason)
                error_writer.writerow([i, error_reason])
                continue
            
            rep_id = seq["header"].split("RepID=")[-1].split(" ")[0]
            writer.writerow([rep_id, prediction_score])
            
            time_remaining = calculate_time_remaining(start_time, i, total_steps)
            print(f"Processed sequence {i} of {total_steps}. Time remaining: {int(time_remaining)} seconds.")

        print("Prediction successful! Output saved to", output_file_name)

except TimeoutException as e:
    error_reason = "Failed to load element or button not found."
    print(error_reason)
    error_writer.writerow(["N/A", error_reason])

except Exception as e:
    error_reason = f"An error occurred: {e}"
    print(error_reason)
    error_writer.writerow(["N/A", error_reason])

finally:
    output_file.close()
    error_file.close()
    driver.quit()
