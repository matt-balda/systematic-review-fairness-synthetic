import sys
import re
from difflib import SequenceMatcher

def normalize_string(text):
    if not text:
        return ""
    # Retorna apenas os caracteres alfanuméricos em minúsculas
    return re.sub(r'[^a-z0-9]', '', text.lower())

def get_similarity(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()

def process_ris(input_file, output_file):
    records = []
    current_record = []
    
    current_doi = ""
    current_title = ""
    current_year = ""
    current_authors = []
    
    print("Lendo o arquivo .ris e extraindo os metadados (DOI, Título, Ano, Autores)...")
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            current_record.append(line)
            
            if line.startswith('DO  - '):
                doi = line[6:].strip().lower()
                doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
                current_doi = doi
            elif line.startswith('TI  - ') or line.startswith('T1  - '):
                # Anexa o título caso ocupe mais de uma linha com mesma tag (incomum, mas possível)
                if not current_title:
                    current_title = line[6:].strip()
                else:
                    current_title += " " + line[6:].strip()
            elif line.startswith('PY  - ') or line.startswith('Y1  - '):
                yr = line[6:].strip()
                match = re.search(r'\d{4}', yr)  # Extrai apenas os 4 dígitos do ano
                if match:
                    current_year = match.group(0)
            elif line.startswith('AU  - ') or line.startswith('A1  - '):
                current_authors.append(line[6:].strip())
                
            if line.startswith('ER  -'):
                norm_title = normalize_string(current_title)
                norm_authors = [normalize_string(a) for a in current_authors]
                first_author_norm = norm_authors[0] if norm_authors else ""
                
                # Salvamos o bloco inteiro de linhas e os metadados extraídos
                records.append({
                    'doi': current_doi,
                    'title': norm_title,
                    'year': current_year,
                    'authors': norm_authors,
                    'first_author': first_author_norm,
                    'lines': current_record
                })
                
                current_record = []
                current_doi = ""
                current_title = ""
                current_year = ""
                current_authors = []

    print(f"Total de registros lidos: {len(records)}")
    print("Aplicando Regras Heurísticas Combinadas...")

    unique_records = []
    duplicate_count = 0
    
    for i, rec in enumerate(records):
        is_duplicate = False
        
        for seen in unique_records:
            # REGRA 1: DOI idêntico (Garantia Absoluta)
            if rec['doi'] and seen['doi'] and rec['doi'] == seen['doi']:
                is_duplicate = True
                break
                
            if not rec['title'] or not seen['title']:
                continue
                
            # REGRA 2: Título Exatamente Igual + Mesmo Ano
            if rec['title'] == seen['title'] and rec['year'] == seen['year']:
                is_duplicate = True
                break
                
            # REGRA 3: Similaridade de Título (> 90%) + Mesmo Ano + Primeiro Autor Similar (> 80%)
            if rec['year'] == seen['year'] and rec['first_author'] and seen['first_author']:
                if get_similarity(rec['first_author'], seen['first_author']) > 0.80:
                     if get_similarity(rec['title'], seen['title']) > 0.90:
                         is_duplicate = True
                         break
            
            # REGRA 4: Similaridade de Título EXTREMAMENTE alta (> 96%) + Ano Igual (Mesmo sem ter autor)
            if rec['year'] == seen['year'] and get_similarity(rec['title'], seen['title']) > 0.96:
                is_duplicate = True
                break

            # REGRA 5: Similaridade de Título (> 92%) + Qualquer Autor que Dê Match (Mesmo se os Anos divergem por 1 ano de preprint/publisher)
            if get_similarity(rec['title'], seen['title']) > 0.92:
                set_a = set(rec['authors'])
                set_b = set(seen['authors'])
                if set_a and set_b:
                    overlap = set_a.intersection(set_b)
                    if len(overlap) > 0:
                        is_duplicate = True
                        break

        if not is_duplicate:
            unique_records.append(rec)
        else:
            duplicate_count += 1

    # Gravar o Output
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for rec in unique_records:
            out_f.writelines(rec['lines'])

    print(f"\nDeduplicação Heurística Completa.")
    print(f"Registros processados: {len(records)}")
    print(f"Registros únicos finais mantidos: {len(unique_records)}")
    print(f"Duplicatas removidas: {duplicate_count}")

if __name__ == '__main__':
    input_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases.ris'
    output_file = '/home/mbmota/Documentos/systematic-review-fairness-synthetic/search/results_merge/merge_bases_dedup_heuristic.ris'
    process_ris(input_file, output_file)
