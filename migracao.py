# Script que migra ping-pong duas VMS e mede o tempo de cada uma de migração com o passar dos ciclos

import requests
import time
import hashlib
import hmac
import base64
import urllib.parse
import csv
import os
import threading
from datetime import datetime

# ================= [ CONFIGURAÇÃO ] =================
API_URL    = "http://192.168.0.2:8080/client/api"
API_KEY    = "xzx_Ue2coANrKQ3jGEuTZxPczGEgBLd8RIJZ6XUjoC3-1FiiQvXFYDCBcnYP-UuuiGFMWBYDFAB7lDkRfFXS4Q"
SECRET_KEY = "MNrLJo0I0R5lcaLGATzyp54qjHswqJbuuSvXlJiGUZEqDxtKb5KeRqv_Vmm4jxFuC-K3Lh9cDaOEiAfaIjQ3kA"

# Lista de VMs para migrar
VM_IDS = [
    "da740461-9e54-42ba-b8f1-d6ddd3da8163",
    "ec07c813-85d3-45dc-886f-a6e05a457971"
]

# Hosts de destino
HOST_A = "38c68349-fb52-432d-bc3a-93d3659e8c4a"
HOST_B = "593e9f80-c980-4e88-9018-d6988b8632c1"

LOG_FILE = "log_migracao.csv"
CHECK_INTERVAL = 1 
# ====================================================

def init_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Data_Inicio", "Ciclo", "VM_ID", "Origem", "Destino", "Duracao_Segundos", "Status"])

def salvar_log(ciclo, vm_id, origem, destino, duracao, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, ciclo, vm_id, origem, destino, f"{duracao:.2f}", status])

def assinar_requisicao(params):
    params['apikey'] = API_KEY
    params['response'] = 'json'
    keys = sorted(params.keys())
    query_parts = [f"{k.lower()}={urllib.parse.quote(str(params[k]), safe='*').lower().replace('+', '%20')}" for k in keys]
    query_string = "&".join(query_parts)
    digest = hmac.new(SECRET_KEY.encode('utf-8'), msg=query_string.encode('utf-8'), digestmod=hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode('utf-8')
    final_params = params.copy()
    final_params['signature'] = signature
    return final_params

def get_current_host(vm_id):
    params = assinar_requisicao({'command': 'listVirtualMachines', 'id': vm_id})
    try:
        r = requests.get(API_URL, params=params)
        return r.json()['listvirtualmachinesresponse']['virtualmachine'][0].get('hostid')
    except: return None

def thread_migracao(vm_id, ciclo):
    """Função que roda em paralelo para cada VM"""
    current_host = get_current_host(vm_id)
    if not current_host:
        print(f"   ⚠️ Não foi possível localizar a VM {vm_id}")
        return

    target_host = HOST_B if current_host == HOST_A else HOST_A
    print(f"🔄 [Ciclo {ciclo}] VM {vm_id[:8]}... movendo para {'HOST B' if target_host == HOST_B else 'HOST A'}")

    inicio_timer = time.time()
    
    params = assinar_requisicao({
        'command': 'migrateVirtualMachine',
        'virtualmachineid': vm_id,
        'hostid': target_host
    })
    
    try:
        r = requests.get(API_URL, params=params)
        job_id = r.json()['migratevirtualmachineresponse']['jobid']
        
        # Aguarda Job
        while True:
            q_params = assinar_requisicao({'command': 'queryAsyncJobResult', 'jobid': job_id})
            res = requests.get(API_URL, params=q_params).json()['queryasyncjobresultresponse']
            if res.get('jobstatus') == 1: # Sucesso
                duracao = time.time() - inicio_timer
                print(f"✅ VM {vm_id[:8]}... migrada em {duracao:.2f}s")
                salvar_log(ciclo, vm_id, current_host, target_host, duracao, "SUCESSO")
                break
            elif res.get('jobstatus') == 2: # Falha
                print(f"❌ Falha na VM {vm_id[:8]}")
                salvar_log(ciclo, vm_id, current_host, target_host, 0, "FALHA")
                break
            time.sleep(CHECK_INTERVAL)
    except Exception as e:
        print(f"❌ Erro na thread da VM {vm_id[:8]}: {e}")

def main():
    init_log()
    ciclo = 1
    print(f"🚀 Iniciando Migração Dupla Paralela (Log: {LOG_FILE})")

    try:
        while True:
            print(f"\n--- Iniciando Ciclo de Paralelismo {ciclo} ---")
            
            threads = []
            for vm in VM_IDS:
                t = threading.Thread(target=thread_migracao, args=(vm, ciclo))
                threads.append(t)
                t.start()

            # Espera as duas threads terminarem para começar o próximo ciclo
            for t in threads:
                t.join()
            
            print(f"✨ Ciclo {ciclo} completo para ambas as VMs.")
            ciclo += 1
            time.sleep(2) # Pequena pausa apenas para respiro da API

    except KeyboardInterrupt:
        print("\n🛑 Teste finalizado.")

if __name__ == "__main__":
    main()
