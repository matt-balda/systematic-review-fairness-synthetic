import os
import sys
import csv
import json
import time
import re
import urllib.request
from urllib.error import URLError

def check_ollama(model="llama3"):
    """Checa a API do Ollama no localhost para ver se ele está vivo e tem o modelo."""
    try:
        req = urllib.request.Request(f"http://localhost:11434/api/tags")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            models = [m['name'] for m in data.get('models', [])]
            if not any(model in m.lower() for m in models):
                return False, f"O modelo '{model}' não foi encontrado no Ollama. Rode: ollama pull {model}"
            return True, ""
    except URLError:
        return False, "Processo do Ollama não está rodando. O servidor local 11434 não respondeu."

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

def read_protocol():
    with open('protocol/inclusion_exclusion.md', 'r', encoding='utf-8') as f:
        inc_exc = f.read()
    with open('protocol/research_questions.md', 'r', encoding='utf-8') as f:
        req_qs = f.read()
    return inc_exc, req_qs

def query_llama(prompt, system_instruction):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "llama3",
        "system": system_instruction,
        "prompt": prompt,
        "format": "json", # Força a saída em modo objeto JSON puro (Ollama native dict)
        "stream": False,
        "options": {
            "temperature": 0.0, # Respostas determinísticas e repetíveis
            "seed": 42
        }
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            model_resp = result.get("response", "{}")
            
            # Limpeza caso o modelo vaze lixo ou alucine fora do JSON
            if model_resp.startswith("```json"):
                model_resp = model_resp.strip("`").strip("json\n")
            model_resp = model_resp.replace('\n', ' ')
            
            return json.loads(model_resp)
    except Exception as e:
        print(f" -> Erro na API do Llama: {e}")
        return None

def main():
    print("=======================================")
    print("🚀 Inciando LLM Local (Ollama + LLaMA 3)")
    print("=======================================")
    is_ready, msg = check_ollama("llama3")
    if not is_ready:
        print(f"\n[ERRO CRÍTICO]: {msg}")
        print("Para resolver:")
        print("1. Abra um terminal do Ubuntu.")
        print("2. Rode: curl -fsSL https://ollama.com/install.sh | sh")
        print("3. Rode: ollama pull llama3")
        sys.exit(1)
        
    print("Conexão ao Ollama localhost:11434 : [OK]")
    inc_exc, req_qs = read_protocol()
    
    strict_anchor = "A medical study using deep learning methods to generate synthetic healthcare data with the explicit aim of promoting fairness, equity, and mitigating algorithmic bias in predictive models for underrepresented human demographic groups."
    
    system_instruction = f"""You are a strict and rigorous senior computer science and health researcher conducting a systematic review.
Evaluate the Title and Abstract against the protocol and the following STRICT ANCHOR CRITERION:
'{strict_anchor}'

To be INCLUDED ('Yes'), the paper MUST EXPLICITLY:
1. Use Deep Learning methods (GANs, Diffusion, etc.).
2. Generate SYNTHETIC healthcare/medical data.
3. Explicitly aim to promote FAIRNESS, EQUITY, or MITIGATE ALGORITHMIC BIAS, particularly for underrepresented human demographic groups.

If the paper only addresses synthetic data without a clear fairness/bias mitigation goal, or if it only addresses fairness without generating synthetic data, it MUST BE EXCLUDED ('No'). Be extremely rigid. Do not assume or extrapolate.

# Protocol (Inclusion / Exclusion Criteria):
{inc_exc}

# Research Questions:
{req_qs}

# Output format schema:
{{
  "included": "Yes" or "No",
  "reason": "Identify the missing requirement (e.g., 'No fairness objective' or 'No synthetic data') or 'N/A'",
  "rationale": "One-sentence rationale based on the strict anchor criterion and exclusion criteria."
}}
"""

    ris_path = 'search/results_clean/merge_bases_dedup_semantic.ris'
    csv_path = 'screening/title_abstract/screening_round1_llama.csv'
    
    records = parse_ris(ris_path)
    print(f"Total de {len(records)} artigos extraídos para inferência.")
    
    processed_titles = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Title' in row:
                    processed_titles.add(row['Title'].strip())

    print(f"Artigos já processados neste CSV: {len(processed_titles)}")
    print("Iniciando varredura lenta (Aperte Ctrl+C para pausar e poder voltar depois a qualquer hora)...\n")

    for i, rec in enumerate(records):
        title = rec.get('title', '').strip()
        if not title or title in processed_titles:
            continue
            
        print(f"[{i+1}/{len(records)}] Processando: {title[:45]}...", end="", flush=True)
        
        prompt = f"Title: {title}\nAbstract: {rec.get('abstract', 'No abstract provided')}"
        
        start_t = time.time()
        result = query_llama(prompt, system_instruction)
        end_t = time.time()
        
        if result:
            inc = str(result.get('included', 'Unsure'))
            # Lidando com falência comum de LLMs Open Source de retornarem Booleanos no lugar de Strings
            if inc.lower() == 'true': inc = 'Yes'
            elif inc.lower() == 'false': inc = 'No'
                
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    rec.get('doi', ''),
                    title,
                    rec.get('year', ''),
                    inc,
                    str(result.get('reason', '')).replace('\n', ' '),
                    str(result.get('rationale', '')).replace('\n', ' ')
                ])
            print(f" [{end_t - start_t:.1f}s] -> '{inc}'", flush=True)
        else:
            print(f" [{end_t - start_t:.1f}s] -> FALHA NA INFERÊNCIA", flush=True)
            time.sleep(1) # delay curto em falha pra nao fritar CPU
            
    print("\nTriagem com Llama Local 100% Finalizada!")

if __name__ == "__main__":
    main()
