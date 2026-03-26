import re
import sys

def normalize_title(title):
    """Remove special characters and spaces for aggressive matching"""
    return re.sub(r'[^a-z0-9]', '', title.lower())

def process_ris(input_file, output_file):
    seen_dois = set()
    seen_titles = set()
    
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
                # Clean up DOI commonly appearing as URLs or having extra spaces
                doi = line[6:].strip().lower()
                doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
                current_doi = doi
            # Extract Title
            elif line.startswith('TI  - ') or line.startswith('T1  - '):
                current_title = line[6:].strip()
                
            # ER indicates end of record
            if line.startswith('ER  -'):
                is_duplicate = False
                
                # Check DOI uniqueness
                if current_doi and current_doi != '':
                    if current_doi in seen_dois:
                        is_duplicate = True
                        
                # Check Title uniqueness if DOI wasn't a duplicate (or didn't exist)
                if not is_duplicate and current_title and current_title != '':
                    norm_title = normalize_title(current_title)
                    if len(norm_title) > 10: # Avoid very short generic titles from marking as duplicates
                        if norm_title in seen_titles:
                            is_duplicate = True
                
                if not is_duplicate:
                    out_f.writelines(current_record)
                    unique_count += 1
                    
                    if current_doi and current_doi != '':
                        seen_dois.add(current_doi)
                    if current_title and current_title != '':
                        norm_title = normalize_title(current_title)
                        if len(norm_title) > 10:
                            seen_titles.add(norm_title)
                else:
                    duplicate_count += 1
                
                # Reset for next record
                current_record = []
                current_doi = None
                current_title = None

    print(f"Deduplication complete.")
    print(f"Total records processed: {unique_count + duplicate_count}")
    print(f"Unique records: {unique_count}")
    print(f"Duplicate records removed: {duplicate_count}")

if __name__ == '__main__':
    input_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases.ris'
    output_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases_dedup.ris'
    process_ris(input_file, output_file)
