import re
import sys
from difflib import SequenceMatcher

def normalize_title(title):
    """Clean the title for baseline comparison"""
    return re.sub(r'[^a-z0-9]', '', title.lower())

def is_fuzzy_duplicate(new_title, seen_titles, threshold=0.90):
    for seen_title in seen_titles:
        # SequenceMatcher measures similarity between 0 and 1
        ratio = SequenceMatcher(None, new_title, seen_title).ratio()
        if ratio >= threshold:
            return True
    return False

def process_ris(input_file, output_file, threshold=0.90):
    seen_dois = set()
    seen_titles = []
    
    current_record = []
    current_doi = None
    current_title = None
    
    unique_count = 0
    duplicate_count = 0
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f, \
         open(output_file, 'w', encoding='utf-8') as out_f:
        
        for line in f:
            current_record.append(line)
            
            # Extract DOI
            if line.startswith('DO  - '):
                # Clean up DOI
                doi = line[6:].strip().lower()
                doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
                current_doi = doi
            # Extract Title
            elif line.startswith('TI  - ') or line.startswith('T1  - '):
                current_title = line[6:].strip()
                
            # ER indicates end of record
            if line.startswith('ER  -'):
                is_duplicate = False
                
                # Check DOI uniqueness (exact)
                if current_doi and current_doi != '':
                    if current_doi in seen_dois:
                        is_duplicate = True
                        
                # Check Title uniqueness (fuzzy)
                if not is_duplicate and current_title and current_title != '':
                    norm_title = normalize_title(current_title)
                    if len(norm_title) > 10: # Only compare substantial titles
                        if is_fuzzy_duplicate(norm_title, seen_titles, threshold):
                            is_duplicate = True
                
                if not is_duplicate:
                    out_f.writelines(current_record)
                    unique_count += 1
                    
                    if current_doi and current_doi != '':
                        seen_dois.add(current_doi)
                    if current_title and current_title != '':
                        norm_title = normalize_title(current_title)
                        if len(norm_title) > 10:
                            seen_titles.append(norm_title)
                else:
                    duplicate_count += 1
                
                # Reset for next record
                current_record = []
                current_doi = None
                current_title = None

    print(f"Fuzzy Deduplication complete (Threshold: {threshold}).")
    print(f"Total records processed: {unique_count + duplicate_count}")
    print(f"Unique records: {unique_count}")
    print(f"Duplicate records removed: {duplicate_count}")

if __name__ == '__main__':
    input_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases.ris'
    output_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases_dedup_fuzzy.ris'
    # Threshold for fuzzy title matching (e.g. 0.90 corresponds to ~90% similarity)
    process_ris(input_file, output_file, threshold=0.90)
