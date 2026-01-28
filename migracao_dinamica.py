import requests
import time
import hashlib
import hmac
import base64
import urllib.parse
from datetime import datetime

# ================= [ CONFIGURAÇÃO ] =================
API_URL    = "http://192.168.0.2:8080/client/api"
API_KEY    = "xzx_Ue2coANrKQ3jGEuTZxPczGEgBLd8RIJZ6XUjoC3-1FiiQvXFYDCBcnYP-UuuiGFMWBYDFAB7lDkRfFXS4Q"
SECRET_KEY = "MNrLJo0I0R5lcaLGATzyp54qjHswqJbuuSvXlJiGUZEqDxtKb5KeRqv_Vmm4jxFuC-K3Lh9cDaOEiAfaIjQ3kA"

VM_ID  = "da740461-9e54-42ba-b8f1-d6ddd3da8163"
HOST_A = "38c68349-fb52-432d-bc3a-93d3659e8c4a"
HOST_B = "593e9f80-c980-4e88-9018-d6988b8632c1"

CHECK_INTERVAL = 2 
# ====================================================

def assinar_requisicao(params):
    params['apikey'] = API_KEY
    params['response'] = 'json'
    keys = sorted(params.keys())
    query_parts = []
    for k in keys:
        val_encoded = urllib.parse.quote(str(params[k]), safe='*').lower().replace('+', '%20')
        query_parts.append(f"{k.lower()}={val_encoded}")
    
    query_string = "&".join(query_parts)
    digest = hmac.new(SECRET_KEY.encode('utf-8'), msg=query_string.encode('utf-8'), digestmod=hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode('utf-8')
    
    final_params = params.copy()
    final_params['signature'] = signature
    return final_params

def get_current_host():
    """Descobre em qual host a VM está agora"""
    params = assinar_requisicao({'command': 'listVirtualMachines', 'id': VM_ID})
    try:
        r = requests.get(API_URL, params=params)
        vm_info = r.json()['listvirtualmachinesresponse']['virtualmachine'][0]
        return vm_info.get('hostid')
    except Exception as e:
        print(f"   ⚠️ Erro ao localizar VM: {e}")
        return None

def aguardar_job(job_id):
    while True:
        params = assinar_requisicao({'command': 'queryAsyncJobResult', 'jobid': job_id})
        try:
            r = requests.get(API_URL, params=params)
            res = r.json()['queryasyncjobresultresponse']
            status = res.get('jobstatus') 
            
            if status == 1:
                return True
            elif status == 2:
                print(f"   ❌ Falha no Job: {res.get('jobresult')}")
                return False
        except:
            pass
        time.sleep(CHECK_INTERVAL)

def migrar(target_host):
    params = assinar_requisicao({
        'command': 'migrateVirtualMachine',
        'virtualmachineid': VM_ID,
        'hostid': target_host
    })
    try:
        r = requests.get(API_URL, params=params)
        data = r.json()
        if 'migratevirtualmachineresponse' in data:
            return aguardar_job(data['migratevirtualmachineresponse']['jobid'])
    except:
        return False

def main():
    ciclo = 1
    print(f"🚀 Iniciando Migração Dinâmica (Auto-Detect)")
    
    try:
        while True:
            # 1. Verifica onde a VM está agora
            current_host = get_current_host()
            
            # 2. Define o destino (Se está no A, vai pro B. Se está no B, vai pro A)
            if current_host == HOST_A:
                target_host = HOST_B
                host_label = "HOST B"
            else:
                target_host = HOST_A
                host_label = "HOST A"

            hora = datetime.now().strftime("%H:%M:%S")
            print(f"\n🔄 [Ciclo {ciclo}] VM está em {current_host}. Migrando para {host_label} ({target_host}) às {hora}")
            
            if migrar(target_host):
                print(f"✅ Sucesso! Concluído em {datetime.now().strftime('%H:%M:%S')}")
                ciclo += 1
            else:
                print("😴 Falha. Tentando novamente em 10s...")
                time.sleep(10)
                
    except KeyboardInterrupt:
        print("\n🛑 Interrompido.")

if __name__ == "__main__":
    main()
