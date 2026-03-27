import os
import json
import csv
import logging
import fitz  # PyMuPDF
import pandas as pd
from ollama import Client

# Configuraçoes
PDF_DIR = 'pdfs'
DATA_EXTRACTION_DIR = 'data_extraction'
OUTPUT_CSV = os.path.join(DATA_EXTRACTION_DIR, 'extracted_features.csv')
MODEL_NAME = 'llama3'
LLM_CLIENT = Client(host='http://localhost:11434')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_text_from_pdf(pdf_path, max_pages=8):
    """Extrai texto das primeiras páginas do PDF."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        # Extrai de até 8 páginas para pegar Resumos e Conclusões
        for i in range(min(max_pages, len(doc))):
            text += doc[i].get_text()
        doc.close()
    except Exception as e:
        logging.error(f"Erro ao ler PDF {pdf_path}: {e}")
    return text

def get_features_from_llm(text, filename):
    """Envia o texto para o Llama 3 e extrai as características."""
    prompt = f"""
    You are an expert in systematic reviews of machine learning and fairness.
    Analyze the following research paper text (from {filename}) and extract specific details in a valid JSON format.
    
    FIELDS TO EXTRACT:
    - methodology_type: The main technique used (e.g., GAN, SMOTE, LLM, etc.)
    - dataset_name: Name of the datasets used (e.g., MIMIC-III, Adult, etc.)
    - bias_classes: Protected attributes addressed (e.g., Race, Gender, Age, etc.)
    - fairness_metrics: Metrics used (e.g., Equalized Odds, Demographic Parity, etc.)
    - main_results: Core quantitative or qualitative findings.
    - limitations: Weaknesses or gaps mentioned by authors.
    - evaluation_scenario: Type of data evaluation (Real, Synthetic, or Hybrid).
    - fairness_definitions: Category of fairness (Group, Individual, or Counterfactual).
    - software_library: Specific tools/libraries mentioned (Fairlearn, PyTorch, etc.)
    - future_work: Directions for subsequent study.
    - main_contribution: One sentence summary of the paper's primary goal.

    Return ONLY a JSON object. If a field is not found, use "Not explicitly mentioned".

    TEXT:
    {text[:8000]} 
    """
    
    try:
        response = LLM_CLIENT.chat(model=MODEL_NAME, messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        # Tenta extrair o JSON da resposta
        content = response['message']['content']
        # Remove eventuais blocos de código markdown
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].strip()
            
        return json.loads(content)
    except Exception as e:
        logging.error(f"Erro ao processar com LLM para {filename}: {e}")
        return {
            "methodology_type": "Error",
            "dataset_name": "Error",
            "bias_classes": "Error",
            "fairness_metrics": "Error",
            "main_contribution": "Error"
        }

def main():
    if not os.path.exists(PDF_DIR):
        logging.error(f"Diretório {PDF_DIR} não encontrado.")
        return

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    results = []

    logging.info(f"Iniciando extração de {len(pdf_files)} PDFs...")

    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        logging.info(f"[{i}/{len(pdf_files)}] Processando: {pdf_file}")
        
        text = extract_text_from_pdf(pdf_path)
        if not text:
            logging.warning(f"Texto vazio para {pdf_file}. Pulando.")
            continue
            
        features = get_features_from_llm(text, pdf_file)
        features['filename'] = pdf_file
        results.append(features)

    # Salvar resultados
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    logging.info(f"Extração concluída! Resultados salvos em: {OUTPUT_CSV}")

if __name__ == '__main__':
    main()
