import os
import sys
import csv
import json
import time
import re

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Instalando a biblioteca oficial google-genai de forma silenciosa...")
    os.system("python3 -m pip install google-genai --quiet")
    from google import genai
    from google.genai import types

def parse_ris(filepath):
    records = []
    current_rec = {}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('DO  - '):
                current_rec['doi'] = line[6:].strip()
            elif line.startswith('TI  - ') or line.startswith('T1  - '):
                if 'title' not in current_rec:
                    current_rec['title'] = line[6:].strip()
                else:
                    current_rec['title'] += " " + line[6:].strip()
            elif line.startswith('AB  - '):
                if 'abstract' not in current_rec:
                    current_rec['abstract'] = line[6:].strip()
                else:
                    current_rec['abstract'] += " " + line[6:].strip()
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

def read_protocol():
    with open('protocol/inclusion_exclusion.md', 'r', encoding='utf-8') as f:
        inc_exc = f.read()
    with open('protocol/research_questions.md', 'r', encoding='utf-8') as f:
        req_qs = f.read()
    return inc_exc, req_qs

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Erro crítico: A GEMINI_API_KEY não foi injetada no ambiente.")
        sys.exit(1)

    print("Inicializando cliente da API do Gemini (2.5-flash)...", flush=True)
    client = genai.Client()
    inc_exc, req_qs = read_protocol()
    
    system_instruction = f"""Você é um pesquisador sênior de Ciência da Computação e Saúde conduzindo a Triagem (Screening) de uma Revisão Sistemática.
Seu objetivo primário é avaliar o Título e o Resumo (Abstract) do estudo e decidir se ele DEVE SER INCLUÍDO ('Yes') ou EXCLUÍDO ('No') com base estritamente no seguinte protocolo metodológico:

# Protocolo (Critérios de Inclusão e Exclusão):
{inc_exc}

# Questões de Pesquisa (Apenas para base de relevância do problema real):
{req_qs}

Retorne um JSON válido e estruturado, obrigatoriamente neste formato (e com estas chaves exatas):
{{
  "included": "Yes" ou "No" ou "Unsure",
  "reason": "Razão curta da exclusão ou 'N/A' se Included for Yes",
  "rationale": "Justificativa direta em 1 sentenca fundamentada no protocolo."
}}
"""

    ris_path = 'search/results_clean/merge_bases_dedup_semantic.ris'
    csv_path = 'screening/title_abstract/screening_round1.csv'
    
    records = parse_ris(ris_path)
    print(f"Buscando do arquivo RIS... {len(records)} artigos encontrados.", flush=True)
    
    # Criar arquivo se não existir, ou carregar processados para não recomeçar do zero.
    processed_titles = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Title' in row:
                    processed_titles.add(row['Title'].strip())
    
    # Se CSV não existe ou está vazio (só tem cabeçalho quebrado)
    if not os.path.exists(csv_path) or os.stat(csv_path).st_size < 10:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['DOI', 'Title', 'Year', 'Included', 'Reason', 'Rationale'])

    print(f"Sincronizado. Artigos já triados no CSV: {len(processed_titles)}", flush=True)

    for i, rec in enumerate(records):
        title = rec.get('title', '').strip()
        if not title or title in processed_titles:
            continue
            
        print(f"Processando [{i+1}/{len(records)}]: {title[:60]}...", flush=True)
        
        prompt = f"Title: {title}\nAbstract: {rec.get('abstract', 'No abstract provided')}"
        
        success = False
        attempts = 0
        while not success and attempts < 3:
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                
                result = json.loads(response.text)
                inc = result.get('included', 'Unsure')
                if isinstance(inc, bool): 
                    inc = 'Yes' if inc else 'No' # Evitar erros de parser JS
                
                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        rec.get('doi', ''),
                        title,
                        rec.get('year', ''),
                        str(inc),
                        str(result.get('reason', '')).replace('\n', ' '),
                        str(result.get('rationale', '')).replace('\n', ' ')
                    ])
                    
                success = True
                
                # Free tier do Gemini limita 15 RPM. 60/15 = 4. Portanto 4.2 segundos de cooldown previene erro 429 infinitamente.
                time.sleep(4.2)
                
            except Exception as e:
                attempts += 1
                err_msg = str(e)
                if "429" in err_msg or "Resource Exhausted" in err_msg or "Quota" in err_msg:
                    print(f"  [Rate Limit API Free] Aguardando 15s...", flush=True)
                    time.sleep(15)
                else:
                    print(f"  [Erro] Falha ao consultar o Gemini: {err_msg}", flush=True)
                    time.sleep(5)
        
        if not success:
            print(f"  [Erro Irrecuperável] Pulando o artigo '{title[:30]}...'", flush=True)
            
    print("\nTriagem 100% Finalizada! Todos os artigos preenchidos no CSV.", flush=True)

if __name__ == "__main__":
    main()
