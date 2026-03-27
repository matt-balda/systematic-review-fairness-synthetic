import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuraçoes
DATA_EXTRACTION_DIR = 'data_extraction'
INPUT_CSV = os.path.join(DATA_EXTRACTION_DIR, 'extracted_features.csv')
PLOT_DIR = os.path.join(DATA_EXTRACTION_DIR, 'plots')

def clean_and_split(series):
    """Limpa e separa valores de uma série de dados (como listas separadas por vírgula)."""
    clean_list = []
    for val in series:
        if pd.isna(val) or val == 'Error' or val == 'Unknown':
            continue
        # Tenta lidar com listas em strings ou strings simples
        items = str(val).split(',')
        for item in items:
            item = item.strip().strip("[]'\"").strip()
            if item and item.lower() != 'error' and item.lower() != 'unknown':
                clean_list.append(item)
    return pd.Series(clean_list)

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Dataset {INPUT_CSV} não encontrado.")
        return
        
    if not os.path.exists(PLOT_DIR):
        os.makedirs(PLOT_DIR)
        
    df = pd.read_csv(INPUT_CSV)
    
    # 1. Gráfico de Metodologias
    plt.figure(figsize=(10, 6))
    methods = clean_and_split(df['methodology_type'])
    if not methods.empty:
        methods.value_counts().head(10).plot(kind='bar', color='skyblue')
        plt.title('Top 10 Metodologias Utilizadas')
        plt.xlabel('Metodologia')
        plt.ylabel('Frequência')
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, 'top_methodologies.png'))
        print(f"Salvo: top_methodologies.png")

    # 2. Gráfico de Bias Classes (Protected Attributes)
    plt.figure(figsize=(10, 6))
    bias_classes = clean_and_split(df['bias_classes'])
    if not bias_classes.empty:
        bias_classes.value_counts().head(10).plot(kind='bar', color='salmon')
        plt.title('Atributos Protegidos Abordados (Bias Classes)')
        plt.xlabel('Classe')
        plt.ylabel('Frequência')
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, 'bias_classes.png'))
        print(f"Salvo: bias_classes.png")

    # 3. Gráfico de Datasets
    plt.figure(figsize=(10, 6))
    datasets = clean_and_split(df['dataset_name'])
    if not datasets.empty:
        datasets.value_counts().head(10).plot(kind='bar', color='lightgreen')
        plt.title('Top 10 Datasets Utilizados')
        plt.xlabel('Dataset')
        plt.ylabel('Frequência')
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, 'top_datasets.png'))
        print(f"Salvo: top_datasets.png")

    # 4. Gráfico de Cenários de Avaliação
    plt.figure(figsize=(8, 5))
    scenarios = clean_and_split(df['evaluation_scenario'])
    if not scenarios.empty:
        scenarios.value_counts().plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=['gold', 'lightblue', 'lightcoral'])
        plt.title('Cenários de Avaliação (Real vs Sintético)')
        plt.ylabel('')
        plt.savefig(os.path.join(PLOT_DIR, 'evaluation_scenarios.png'))
        print(f"Salvo: evaluation_scenarios.png")

    # 5. Gráfico de Definições de Justiça
    plt.figure(figsize=(10, 6))
    definitions = clean_and_split(df['fairness_definitions'])
    if not definitions.empty:
        definitions.value_counts().plot(kind='barh', color='orchid')
        plt.title('Definições de Justiça Aplicadas')
        plt.xlabel('Frequência')
        plt.ylabel('Definição')
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, 'fairness_definitions.png'))
        print(f"Salvo: fairness_definitions.png")

    print(f"\nVisualização concluída! Gráficos salvos em: {PLOT_DIR}")

if __name__ == '__main__':
    main()
