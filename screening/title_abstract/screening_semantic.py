import sys
import csv
import re
import warnings

# Silenciando warnings inofensivos da lib 
warnings.filterwarnings("ignore")

try:
    import torch
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("A biblioteca sentence-transformers não foi encontrada.")
    print("Execute: python3 -m pip install sentence-transformers")
    sys.exit(1)

def parse_ris(filepath):
    records = []
    current_rec = {}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('DO  - '):
                current_rec['doi'] = line[6:].strip()
            elif line.startswith('TI  - ') or line.startswith('T1  - '):
                current_rec['title'] = current_rec.get('title', '') + (" " if current_rec.get('title') else "") + line[6:].strip()
            elif line.startswith('AB  - '):
                current_rec['abstract'] = current_rec.get('abstract', '') + (" " if current_rec.get('abstract') else "") + line[6:].strip()
            elif line.startswith('PY  - ') or line.startswith('Y1  - '):
                yr = line[6:].strip()
                match = re.search(r'\d{4}', yr)
                if match:
                    current_rec['year'] = match.group(0)
            elif line.startswith('ER  -'):
                if current_rec.get('title') or current_rec.get('abstract'):
                    records.append(current_rec)
                current_rec = {}
    return records

def classify_semantic():
    print("=============================================")
    print("Iniciando Triagem Semântica Local (Sem API)")
    print("=============================================")
    print("1. Carregando modelo 'all-MiniLM-L6-v2' (Pode levar uns 5 segundos)...")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # FRASE-ÂNCORA: O resumo do que seria o artigo perfeito segundo o Protocolo.
    anchor_text = "A medical study using deep learning methods to generate synthetic healthcare data with the explicit aim of promoting fairness, equity, and mitigating algorithmic bias in predictive models for underrepresented human demographic groups."
    anchor_emb = model.encode(anchor_text, convert_to_tensor=True)
    
    ris_path = 'search/results_clean/merge_bases_dedup_semantic.ris'
    csv_path = 'screening/title_abstract/screening_round1.csv'
    
    records = parse_ris(ris_path)
    print(f"2. Extraídos {len(records)} artigos brutos do arquivo .ris sem duplicatas.")
    print("3. Calculando Distância de Similaridade (Cosine Scaled) para todos os artigos...", flush=True)

    # Como mudamos do método Manual (que falhou) para Semântico,
    # apagaremos a versão pela metade do CSV e regravaremos ele 100% categorizado.
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['DOI', 'Title', 'Year', 'Included', 'Reason', 'Rationale'])
        
        for i, rec in enumerate(records):
            title = rec.get('title', '').strip()
            abstract = rec.get('abstract', '').strip()
            
            # Text to evaluate = Title + Abstract
            text_to_eval = f"{title}. {abstract}"
            if len(text_to_eval) < 10:
                continue
                
            art_emb = model.encode(text_to_eval, convert_to_tensor=True)
            cos_score = util.cos_sim(anchor_emb, art_emb).item()
            
            # Limites Semânticos Base (Adaptáveis dependendo do uso)
            # all-MiniLM-L6-v2 costuma pontuar entre 0.1 e 0.6 em similaridade de tópicos textuais genéricos vs complexos.
            if cos_score >= 0.60:
                included = "Yes"
                reason = "N/A"
                rationale_prefix = "High Topic Match"
            elif cos_score >= 0.50:
                included = "Unsure"
                reason = "Borderline Alignment"
                rationale_prefix = "Borderline Topic Match"
            else:
                included = "No"
                reason = "Low Topic Alignment"
                rationale_prefix = "Poor Topic Match"
                
            rationale = f"{rationale_prefix} (Cos Similarity: {cos_score:.3f})"
            
            writer.writerow([
                rec.get('doi', ''),
                title,
                rec.get('year', ''),
                included,
                reason,
                rationale
            ])
            
            if (i+1) % 100 == 0:
                print(f"   => Artigos calculados: {i+1} / {len(records)}", flush=True)

    print("\n[SUCESSO] Triagem Semântica concluída.")
    print(f"Abra o arquivo '{csv_path}' e ordene pela coluna 'Rationale' do maior para o menor!")

if __name__ == '__main__':
    classify_semantic()
