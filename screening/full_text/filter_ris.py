import csv

def load_approved_data(csv_path):
    approved_dois = set()
    approved_titles = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Included', '').strip().lower() == 'yes':
                doi = row.get('DOI', '').strip()
                title = row.get('Title', '').strip().lower()
                if doi:
                    approved_dois.add(doi)
                if title:
                    approved_titles.add(title)
    return approved_dois, approved_titles

def filter_ris(input_ris, output_ris, approved_dois, approved_titles):
    with open(input_ris, 'r', encoding='utf-8') as fin, \
         open(output_ris, 'w', encoding='utf-8') as fout:
        
        current_record = []
        is_matched = False
        count = 0
        
        for line in fin:
            current_record.append(line)
            
            # Match by DOI
            if line.startswith('DO  - '):
                doi_in_ris = line.replace('DO  - ', '').strip()
                if doi_in_ris in approved_dois:
                    is_matched = True
            
            # Match by Title (TI  - )
            if line.startswith('TI  - '):
                title_in_ris = line.replace('TI  - ', '').strip().lower()
                if title_in_ris in approved_titles:
                    is_matched = True
            
            # End of record
            if line.startswith('ER  -'):
                if is_matched:
                    fout.writelines(current_record)
                    count += 1
                
                # Reset for next record
                current_record = []
                is_matched = False
                
        return count

def main():
    CSV_FILE = '../title_abstract/screening_round1.csv'
    RIS_INPUT = '../../search/results_clean/merge_bases_dedup_semantic.ris'
    RIS_OUTPUT = 'screened_articles.ris'
    
    print(f"Buscando DOIs e Títulos aprovados em: {CSV_FILE}")
    approved_dois, approved_titles = load_approved_data(CSV_FILE)
    print(f"Total de itens aprovados: {len(approved_titles)}")
    
    print(f"Filtrando RIS: {RIS_INPUT}")
    matched_count = filter_ris(RIS_INPUT, RIS_OUTPUT, approved_dois, approved_titles)
    
    print(f"✅ Filtro concluído! {matched_count} artigos foram movidos para {RIS_OUTPUT}")

if __name__ == '__main__':
    main()
