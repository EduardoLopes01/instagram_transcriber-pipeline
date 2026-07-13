# 🎥 Instagram AI Transcriber & Cost-Tracking Pipeline

> Um assistente inteligente e multiversátil que automatiza o download, transcrição e análise financeira (FinOps) de Reels e vídeos do Instagram de ponta a ponta.

---

## 🌟 O que é o Projeto?

Este projeto é um pipeline automatizado em Python projetado para criadores de conteúdo, gerentes de produto (PMs), profissionais de marketing e desenvolvedores que buscam minerar dados de vídeo do Instagram com eficiência e baixo custo. 

Ele extrai o conteúdo em áudio do vídeo do Instagram e gera transcrições literais de altíssima qualidade utilizando Inteligência Artificial Generativa. Simultaneamente, o pipeline computa em tempo real a economia dos tokens consumidos e o custo financeiro exato (em BRL e USD) de cada requisição, centralizando tudo em um painel visual dinâmico.

---

## 🚀 Funcionalidades Principais

- **Extração Automatizada de Mídia:** Reconhece e processa links diretos de Reels, posts e vídeos do Instagram.
- **Normalização com ActivityStreams 2.0:** Utiliza a robusta `KonbiniAPI` para estruturar os dados de forma limpa e padronizada (padrão W3C).
- **Transcrição Multimodal (IA):** Faz o upload de mídia e gera transcrições literais e contextuais em português usando o modelo de última geração `gemini-3.1-flash-lite`.
- **Assistente de Configuração Inteligente (UX/DX):** O script detecta automaticamente chaves ausentes e executa um assistente interativo no próprio terminal para cadastrá-las na primeira execução, eliminando a necessidade de gerenciar arquivos ocultos manualmente.
- **FinOps & Economia de Tokens:** Monitora e exibe estatísticas precisas de tokens de Entrada (vídeo/prompt) e Saída (texto) e calcula custos reais em Real Brasileiro (BRL) e Dólar (USD).
- **Dashboard Visual Integrado:** Fornece um painel em HTML moderno (Glassmorphism Dark Mode) com tabelas de histórico e um simulador de projeção de custos para tomadas de decisão.

---

## 📊 Estudo de Viabilidade Financeira (Unit Economics)

Uma das maiores dores ao escalar produtos baseados em IA Generativa é o controle de custos. Este pipeline foi desenhado para ser extremamente otimizado:

| Componente | Quantidade Consumida | Custo Unitário (USD) | Custo Unitário (BRL) | % do Custo |
| :--- | :---: | :---: | :---: | :---: |
| **KonbiniAPI (Raspagem)** | 1 requisição | $0,01000000 | R$ 0,05600000 | ~91,6% |
| **Gemini Input (Vídeo)** | 10.446 tokens | $0,00078345 | R$ 0,00438732 | ~7,2% |
| **Gemini Output (Texto)** | 418 tokens | $0,00012540 | R$ 0,00070224 | ~1,2% |
| **Custo Total por Reel** | - | **$0,01090885** | **R$ 0,06108956** | **100%** |

*Parâmetros: Câmbio comercial de referência: $1 USD = R$ 5,60 BRL.*

### ☕ Exemplo de Escala
Processar **1.000 Reels do Instagram por mês** custa aproximadamente **R$ 61,09** no total. Isso equivale ao preço de **12 cafezinhos de R$ 5,00**, tornando este pipeline extremamente competitivo e ideal para análises de mercado em larga escala.

---

## 🛠️ Como Instalar e Rodar

### 1. Requisitos Prévios
Certifique-se de ter o Python 3.10+ instalado no seu computador.

### 2. Clonar o Repositório
```bash
git clone https://github.com/EduardoLopes01/instagram_transcriber-pipeline.git
cd instagram_transcriber-pipeline
```

### 3. Configurar Ambiente Virtual e Dependências
Crie o ambiente isolado do Python e instale as bibliotecas necessárias:
```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # No Mac/Linux
venv\Scripts\activate     # No Windows

# Instalar dependências
pip install -r requirements.txt
```

### 4. Executar o Pipeline
Escolha a URL do vídeo do Instagram que deseja transcrever e execute:
```bash
python scraper.py "URL_DO_REEL_AQUI"
```

> 💡 **Primeira Execução:** O assistente de terminal iniciará automaticamente e solicitará as suas chaves de API da **KonbiniAPI** e do **Gemini**. Cole-as no prompt e o arquivo de configuração `.env` será criado de forma segura.

---

## 📈 Visualizando o Painel de Custos (Dashboard)

Após rodar o script, um arquivo contendo as métricas de histórico de chamadas (`history.js`) será gerado na pasta raiz.

Para abrir o painel:
1. Abra a pasta do projeto no seu explorador de arquivos.
2. Dê dois cliques no arquivo **`dashboard.html`** (ele abrirá diretamente no Safari, Chrome ou seu navegador padrão).
3. Monitore o histórico de execuções, tempos médios e use a calculadora interativa na lateral para simular custos de volumes maiores.

---

## 🔒 Segurança de Dados e Credenciais
Este repositório está configurado com um arquivo `.gitignore` que impede que suas chaves privadas contidas no arquivo `.env` sejam enviadas para a nuvem pública do GitHub. Nunca compartilhe sua chave real com terceiros.
