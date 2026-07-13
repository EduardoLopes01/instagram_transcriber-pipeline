#!/usr/bin/env python3
import os
import sys
import re
import time
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# Definir o diretorio base absoluto do script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carregar variaveis de ambiente do arquivo .env na raiz do projeto
load_dotenv(os.path.join(BASE_DIR, ".env"))

KONBINI_API_KEY = os.getenv("KONBINI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

def parse_args():
    if len(sys.argv) < 2:
        print("Uso: python scraper.py <Instagram URL ou Shortcode>")
        print("Exemplo: python scraper.py https://www.instagram.com/reel/CybWViruta1/")
        sys.exit(1)
    return sys.argv[1]

def extract_shortcode(input_str: str) -> str:
    """
    Extrai o shortcode do Instagram a partir de uma URL ou valida se o input já é um shortcode.
    """
    input_str = input_str.strip()
    
    # Se já for um shortcode simples
    if re.match(r'^[A-Za-z0-9_-]+$', input_str):
        return input_str
        
    # Casos de URL:
    # https://www.instagram.com/p/CybWViruta1/
    # https://www.instagram.com/reel/CybWViruta1/
    # https://www.instagram.com/reels/CybWViruta1/
    # https://www.instagram.com/tv/CybWViruta1/
    match = re.search(r'/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', input_str)
    if match:
        return match.group(1)
        
    raise ValueError(f"Não foi possível extrair o shortcode do Instagram a partir de: {input_str}")

def fetch_post_data(shortcode: str) -> dict:
    """
    Consulta a KonbiniAPI para obter os metadados do post no padrão ActivityStreams 2.0.
    """
    url = f"https://api.konbiniapi.com/v1/instagram/posts/{shortcode}"
    headers = {
        "Authorization": f"Bearer {KONBINI_API_KEY}"
    }
    
    print(f"[*] Consultando KonbiniAPI para o shortcode: {shortcode}...")
    response = requests.get(url, headers=headers)
    
    # Em caso de falha, imprime o JSON de erro para diagnóstico rápido
    if response.status_code != 200:
        print(f"[!] Erro ao consultar a API. Status HTTP: {response.status_code}")
        try:
            print("[!] Resposta da API:", response.json())
        except Exception:
            print("[!] Corpo da resposta:", response.text)
        response.raise_for_status()
        
    return response.json()

def extract_video_url(post_data: dict) -> str:
    """
    Extrai a URL direta do vídeo (.mp4) a partir da resposta JSON ActivityStreams 2.0 da KonbiniAPI.
    """
    data = post_data.get("data", {})
    if not data:
        raise ValueError("JSON retornado pela KonbiniAPI não contém a chave 'data'.")
        
    # Caso 1: O post principal tem o anexo do vídeo diretamente
    attachments = data.get("attachment", [])
    for att in attachments:
        # Procuramos por tipo Video e uma lista de URLs
        if att.get("type") == "Video" and att.get("url"):
            return att["url"][0]
            
    # Caso 2: Se for um carrossel, inspecionamos os itens
    items = data.get("items", [])
    for item in items:
        item_attachments = item.get("attachment", [])
        for att in item_attachments:
            if att.get("type") == "Video" and att.get("url"):
                print("[*] Vídeo encontrado dentro do primeiro item de carrossel.")
                return att["url"][0]

    # Caso 3: Fallback amplo em qualquer anexo com tipo Video ou URL mp4
    for att in attachments:
        if att.get("url"):
            url = att["url"][0]
            if ".mp4" in url or "video" in att.get("mediaType", ""):
                return url

    # Caso 4: Se o próprio post é do tipo Video e tem URL
    if data.get("type") == "Video" and data.get("url"):
        return data["url"]

    # Se chegarmos aqui, debugamos a estrutura real
    print("[!] Não foi possível localizar o vídeo nos locais padrão. Estrutura do JSON:")
    import pprint
    pprint.pprint(data)
    raise ValueError("Nenhuma URL de vídeo (.mp4) foi encontrada nos metadados do post.")

def download_video(video_url: str, output_path: str):
    """
    Faz o download do vídeo em chunks para evitar estouro de memória.
    """
    print(f"[*] Iniciando download do vídeo...")
    response = requests.get(video_url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    bytes_downloaded = 0
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                bytes_downloaded += len(chunk)
                if total_size > 0:
                    percent = (bytes_downloaded / total_size) * 100
                    print(f"\rDownloading: {percent:.2f}% ({bytes_downloaded}/{total_size} bytes)", end="", flush=True)
    print("\n[+] Download concluído com sucesso!")

def save_to_history(run_data: dict):
    """
    Salva os dados de execução no arquivo history.js no formato 'const HISTORY_DATA = [...];'
    bypassando restrições de CORS para leitura local direta.
    """
    history_file = os.path.join(BASE_DIR, "history.js")
    import json
    
    runs = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Extrair o array JSON de dentro de const HISTORY_DATA = [...];
                match = re.search(r'const HISTORY_DATA\s*=\s*(\[.*?\])\s*;', content, re.DOTALL)
                if match:
                    runs = json.loads(match.group(1))
        except Exception as e:
            print(f"[!] Erro ao ler histórico: {e}")
            
    # Remover execuções anteriores com o mesmo shortcode para evitar duplicados
    runs = [r for r in runs if r.get("shortcode") != run_data["shortcode"]]
    runs.append(run_data)
    
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            f.write(f"const HISTORY_DATA = {json.dumps(runs, indent=2)};\n")
        print("[+] Histórico de execuções atualizado com sucesso em 'history.js'.")
    except Exception as e:
        print(f"[!] Erro ao gravar histórico: {e}")

def transcribe_video(video_path: str) -> tuple:
    """
    Faz o upload do vídeo para a Gemini API, aguarda o processamento, gera a transcrição
    e retorna o texto e os dados de tokens.
    """
    print(f"[*] Inicializando cliente do Gemini SDK com o modelo: {GEMINI_MODEL}...")
    client = genai.Client() # Autentica usando a variável GEMINI_API_KEY
    
    print(f"[*] Fazendo upload do vídeo '{video_path}' para o Gemini...")
    video_file = client.files.upload(file=video_path)
    print(f"[+] Upload finalizado. ID do arquivo no Gemini: {video_file.name}")
    
    prompt_tokens = 0
    candidates_tokens = 0
    
    try:
        # Polling do status do arquivo até que mude para ACTIVE
        print("[*] Aguardando processamento do vídeo no servidor do Gemini...")
        while True:
            file_info = client.files.get(name=video_file.name)
            state = file_info.state.name
            print(f" -> Estado atual do processamento: {state}")
            if state == "ACTIVE":
                break
            elif state in ["FAILED", "REJECTED"]:
                raise RuntimeError(f"O processamento do vídeo no Gemini falhou com estado: {state}")
            time.sleep(5)
            
        print("[*] Gerando transcrição...")
        prompt = (
            "Faça a transcrição completa e literal do conteúdo falado neste vídeo em português. "
            "Ignore músicas de fundo ou barulhos irrelevantes. Se houver mais de uma pessoa falando, "
            "tente identificar as falas separadamente se possível. "
            "Retorne apenas o texto transcrito formatado de forma limpa."
        )
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[video_file, prompt]
        )
        
        # Obter estatísticas do uso de tokens e exibir
        usage = response.usage_metadata
        if usage:
            prompt_tokens = usage.prompt_token_count
            candidates_tokens = usage.candidates_token_count
            print("\n================ Usage Stats ================")
            print(f"Prompt (Input) Tokens: {prompt_tokens}")
            print(f"Candidates (Output) Tokens: {candidates_tokens}")
            print(f"Total Tokens: {prompt_tokens + candidates_tokens}")
            
            input_cost = (prompt_tokens / 1_000_000) * 0.075
            output_cost = (candidates_tokens / 1_000_000) * 0.30
            total_cost = input_cost + output_cost
            print(f"Custo Estimado (Input): ${input_cost:.8f}")
            print(f"Custo Estimado (Output): ${output_cost:.8f}")
            print(f"Custo Total Estimado: ${total_cost:.8f} USD")
            print("=============================================\n")
            
        return response.text, prompt_tokens, candidates_tokens
        
    finally:
        # Garantir a limpeza do arquivo para liberar recursos no Gemini
        print("[*] Limpando arquivo temporário do Gemini...")
        try:
            client.files.delete(name=video_file.name)
            print("[+] Arquivo temporário removido com sucesso.")
        except Exception as e:
            print(f"[!] Erro ao remover arquivo temporário do Gemini: {e}")

def check_and_prompt_keys():
    """
    Verifica se o arquivo .env e as chaves estão configurados.
    Caso contrário, auxilia o usuário interativamente a criar o arquivo,
    evitando que usuários leigos precisem gerenciar arquivos ocultos (.*) no sistema.
    """
    global KONBINI_API_KEY, GEMINI_API_KEY
    env_path = os.path.join(BASE_DIR, ".env")
    
    needs_setup = False
    if not os.path.exists(env_path):
        needs_setup = True
    else:
        load_dotenv(env_path, override=True)
        KONBINI_API_KEY = os.getenv("KONBINI_API_KEY")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if (not KONBINI_API_KEY or KONBINI_API_KEY.strip() == "" or KONBINI_API_KEY == "sua_chave_konbini_aqui" or
            not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "" or GEMINI_API_KEY == "sua_chave_gemini_aqui"):
            needs_setup = True
            
    if needs_setup:
        print("\n======================================================")
        print("          ASSISTENTE DE CONFIGURAÇÃO INICIAL")
        print("   As chaves de API do pipeline não foram encontradas.")
        print("   Vamos criar o seu arquivo de configuração (.env) agora.")
        print("======================================================\n")
        
        try:
            choice = input("Deseja configurar suas chaves de API agora? (S/n): ").strip().lower()
            if choice == 'n':
                print("[!] Execução abortada. Crie e configure o arquivo .env manualmente.")
                sys.exit(1)
                
            konbini_key = input("1. Digite sua KONBINI_API_KEY: ").strip()
            gemini_key = input("2. Digite sua GEMINI_API_KEY: ").strip()
            
            if not konbini_key or not gemini_key:
                print("[!] Erro: Ambas as chaves são obrigatórias para rodar o pipeline.")
                sys.exit(1)
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"# Credenciais da API KonbiniAPI\nKONBINI_API_KEY={konbini_key}\n\n")
                f.write(f"# Credenciais da API do Gemini\nGEMINI_API_KEY={gemini_key}\n\n")
                f.write(f"# Configurações do pipeline\nGEMINI_MODEL=gemini-3.1-flash-lite\n")
                
            print(f"\n[+] Configurações salvas com sucesso em: {env_path}")
            
            # Recarregar as variáveis no ambiente atual
            load_dotenv(env_path, override=True)
            KONBINI_API_KEY = os.getenv("KONBINI_API_KEY")
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            print("[+] Configuração carregada. Iniciando execução do pipeline...\n")
            
        except KeyboardInterrupt:
            print("\n[!] Configuração cancelada pelo usuário.")
            sys.exit(1)

def main():
    # Validar e configurar chaves de API interativamente se necessário
    check_and_prompt_keys()

    input_str = parse_args()
    
    try:
        shortcode = extract_shortcode(input_str)
    except ValueError as e:
        print(f"[!] {e}")
        sys.exit(1)
        
    # Definir caminhos de arquivos absolutos
    downloads_dir = os.path.join(BASE_DIR, "downloads")
    transcripts_dir = os.path.join(BASE_DIR, "transcripts")
    os.makedirs(downloads_dir, exist_ok=True)
    os.makedirs(transcripts_dir, exist_ok=True)
    
    video_path = os.path.join(downloads_dir, f"{shortcode}.mp4")
    transcript_path = os.path.join(transcripts_dir, f"{shortcode}.txt")
    
    start_time = time.time()
    
    try:
        # Fase 2: Obter dados e baixar vídeo
        post_data = fetch_post_data(shortcode)
        video_url = extract_video_url(post_data)
        print(f"[+] URL direta do vídeo encontrada: {video_url}")
        
        download_video(video_url, video_path)
        
        # Fase 3: Transcrição via Gemini API
        print(f"[*] Iniciando transcrição com Gemini...")
        transcript_text, prompt_tokens, candidates_tokens = transcribe_video(video_path)
        
        # Salvar transcrição em arquivo
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
            
        elapsed_time = time.time() - start_time
        
        # Calcular custos reais em USD e BRL (Taxa de 1 USD = 5.60 BRL)
        usd_input_rate = 0.075 / 1_000_000
        usd_output_rate = 0.30 / 1_000_000
        gemini_usd_cost = (prompt_tokens * usd_input_rate) + (candidates_tokens * usd_output_rate)
        
        konbini_usd_cost = 0.01  # $0.01 por chamada
        total_usd_cost = gemini_usd_cost + konbini_usd_cost
        
        exchange_rate = 5.60
        total_brl_cost = total_usd_cost * exchange_rate
        
        # Estruturar o objeto de histórico
        run_data = {
            "shortcode": shortcode,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "input_tokens": prompt_tokens,
            "output_tokens": candidates_tokens,
            "total_tokens": prompt_tokens + candidates_tokens,
            "gemini_cost_usd": gemini_usd_cost,
            "gemini_cost_brl": gemini_usd_cost * exchange_rate,
            "konbini_cost_usd": konbini_usd_cost,
            "konbini_cost_brl": konbini_usd_cost * exchange_rate,
            "total_cost_usd": total_usd_cost,
            "total_cost_brl": total_brl_cost,
            "execution_time_seconds": round(elapsed_time, 2)
        }
        
        save_to_history(run_data)
        
        print(f"\n[+] Transcrição salva com sucesso em: {transcript_path}")
        print("\n--- Transcrição ---")
        print(transcript_text)
        print("-------------------\n")
        
    except Exception as e:
        print(f"\n[!] Ocorreu um erro durante a execução: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
