import sys
import re

try:
    import torch
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("Error: The 'sentence-transformers' library is required for semantic deduplication.")
    print("Please install it by running: pip install sentence-transformers")
    sys.exit(1)

def process_ris(input_file, output_file, threshold=0.85):
    print("Loading semantic model 'all-MiniLM-L6-v2' (this might take a moment to download on first run)...")
    # A fast and powerful model for mapping sentences into semantic vectors
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    current_record = []
    current_doi = None
    current_title = None
    
    records = [] # Array of (doi, title, raw_lines)
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            current_record.append(line)
            
            if line.startswith('DO  - '):
                doi = line[6:].strip().lower()
                doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
                current_doi = doi
            elif line.startswith('TI  - ') or line.startswith('T1  - '):
                current_title = line[6:].strip()
                
            if line.startswith('ER  -'):
                records.append((current_doi, current_title, current_record))
                current_record = []
                current_doi = None
                current_title = None

    print(f"Total records read: {len(records)}")
    print(f"Comparing embeddings semantically with similarity threshold >= {threshold}...")
    
    unique_records = []
    duplicate_count = 0
    seen_dois = set()
    seen_embeddings = []
    
    for i, (doi, title, record_lines) in enumerate(records):
        is_duplicate = False
        
        # 1. Exact DOI match
        if doi and doi != '':
            if doi in seen_dois:
                is_duplicate = True
        
        # 2. Semantic Title match
        if not is_duplicate and title and title != '':
            # Generate the embedding tensor for the current title
            title_emb = model.encode(title, convert_to_tensor=True)
            
            if seen_embeddings:
                # Stack all prev embeddings and compute cosine similarity
                seen_stack = torch.stack(seen_embeddings)
                similarities = util.cos_sim(title_emb, seen_stack)[0] 
                max_sim = torch.max(similarities).item()
                
                if max_sim >= threshold:
                    is_duplicate = True
            
        if not is_duplicate:
            unique_records.append(record_lines)
            if doi and doi != '':
                seen_dois.add(doi)
            if title and title != '':
                seen_embeddings.append(title_emb)
        else:
            duplicate_count += 1
            
        if (i+1) % 100 == 0:
            print(f"Processed {i+1} / {len(records)} records...")

    # Write output
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for record_lines in unique_records:
            out_f.writelines(record_lines)
            
    print(f"Semantic Deduplication complete (Threshold: {threshold}).")
    print(f"Total records processed: {len(records)}")
    print(f"Unique records: {len(unique_records)}")
    print(f"Duplicate records removed: {duplicate_count}")

if __name__ == '__main__':
    input_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases.ris'
    output_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases_dedup_semantic.ris'
    
    # 0.85 threshold is very strong for semantic similarity
    process_ris(input_file, output_file, threshold=0.85)
