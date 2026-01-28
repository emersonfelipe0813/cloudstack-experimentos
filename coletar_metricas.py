#Script para fazer a coleta de métricas da máquina host que roda esse código

import psutil
import time
import csv
import os
from datetime import datetime

# Nome do arquivo de log
LOG_FILE = "metricas.csv"

def init_csv():
    """Cria o arquivo com cabeçalho se não existir"""
    if not os.path.exists(LOG_FILE):
        headers = [
            "DataHora", 
            "CPU_Uso(%)", 
            "RAM_Usada(MB)", 
            "Disco_Usado(GB)", 
            "Rede_Enviado(KB/s)", 
            "Rede_Recebido(KB/s)"
        ]
        with open(LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

def coletar():
    init_csv()
    
    # Inicializa contadores de rede para cálculo de velocidade
    net_io_antigo = psutil.net_io_counters()
    time.sleep(1) # Aguarda 1s para ter o primeiro delta de velocidade

    print(f"📡 Coletando métricas em: {LOG_FILE}")
    print("Pressione [CTRL+C] para parar.")

    try:
        while True:
            # 1. Data e Hora
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 2. CPU (%)
            cpu_uso = psutil.cpu_percent(interval=None)

            # 3. RAM Usada (MB)
            ram_usada = round(psutil.virtual_memory().used / 1024 / 1024, 2)

            # 4. Disco Usado (GB) - Raiz '/'
            disco_usado = round(psutil.disk_usage('/').used / (1024**3), 2)

            # 5. Rede (Velocidade em KB/s)
            net_io_novo = psutil.net_io_counters()
            
            # Diferença de bytes (Novo - Antigo)
            bytes_sent = net_io_novo.bytes_sent - net_io_antigo.bytes_sent
            bytes_recv = net_io_novo.bytes_recv - net_io_antigo.bytes_recv
            
            # Converte para KB/s (dividir por 1024)
            # O loop tem um sleep de 10s no final, então dividimos pelo tempo decorrido total (~10s)
            # Para simplificar, assumimos a média do intervalo
            tempo_intervalo = 10 
            sent_kbs = round((bytes_sent / 1024) / tempo_intervalo, 2)
            recv_kbs = round((bytes_recv / 1024) / tempo_intervalo, 2)
            
            # Atualiza referência para próxima volta
            net_io_antigo = net_io_novo

            # Salva no CSV
            with open(LOG_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    data_hora, 
                    cpu_uso, 
                    ram_usada, 
                    disco_usado, 
                    sent_kbs, 
                    recv_kbs
                ])
            
            # Mostra na tela para acompanhamento
            print(f"[{data_hora}] CPU: {cpu_uso}% | RAM: {ram_usada}MB | Rede In: {recv_kbs}KB/s")

            # Intervalo de coleta
            time.sleep(tempo_intervalo)

    except KeyboardInterrupt:
        print("\n🛑 Coleta finalizada.")

if __name__ == "__main__":
    coletar()
