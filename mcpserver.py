import os
import sys
import time
from mcp.server.mcpserver import MCPServer
from proxmoxer import ProxmoxAPI
import paramiko

# Inizializzazione del Server MCP
mcp = MCPServer("Proxmox Middleware")

# Connessione con l'Hypervisor
def get_proxmox_client() -> ProxmoxAPI:
    """
    Inizializza e restituisce il client REST per Proxmox.
    Le credenziali vengono lette in modo sicuro dalle variabili d'ambiente.
    """
    host = os.environ.get("PROXMOX_HOST")
    user = os.environ.get("PROXMOX_USER")
    token_name = os.environ.get("PROXMOX_TOKEN_NAME")
    token_value = os.environ.get("PROXMOX_TOKEN_VALUE")

    if not all([host, user, token_name, token_value]):
        print("Errore: Credenziali Proxmox mancanti.", file=sys.stderr)
        sys.exit(1)

    return ProxmoxAPI(
        host,
        user=user,
        token_name=token_name,
        token_value=token_value,
        verify_ssl=False
    )

# UC1: Ispezione e Monitoraggio
@mcp.tool()
def list_vms() -> str:
    """
    Recupera la lista di tutte le Macchine Virtuali (VM) e i container (LXC)
    presenti sul server Proxmox, inclusi i loro ID, nomi e lo stato di accensione.
    """
    proxmox = get_proxmox_client()
    risultato = []
    
    try:
        for node in proxmox.nodes.get():
            node_name = node['node']
            
            for vm in proxmox.nodes(node_name).qemu.get():
                nome = vm.get('name', 'N/A')
                risultato.append(f"Node: {node_name} | VMID: {vm['vmid']} | Nome: {nome} | Stato: {vm['status']} | Tipo: VM")
                
            for lxc in proxmox.nodes(node_name).lxc.get():
                nome = lxc.get('name', 'N/A')
                risultato.append(f"Node: {node_name} | VMID: {lxc['vmid']} | Nome: {nome} | Stato: {lxc['status']} | Tipo: LXC")
                
        return "\n".join(risultato) if risultato else "Nessuna risorsa trovata sul server."
        
    except Exception as e:
        return f"Errore durante la comunicazione con Proxmox: {str(e)}"

#UC2: Gestione del ciclo di vita e provisioning delle istanze
@mcp.tool()
def manage_vm_state(node: str, vm_id: int, resource_type: str, action: str) -> str:
    """
    [ATTENZIONE: AZIONE CRITICA - HUMAN-IN-THE-LOOP RICHIESTO]
    Gestisce il ciclo di vita (accensione, spegnimento, riavvio) di una VM o LXC.
    Azioni permesse: 'start', 'stop', 'reboot'.
    
    VINCOLO OPERATIVO OBBLIGATORIO:
    Prima di invocare questo tool (specialmente per 'stop' o 'reboot'), DEVI fermare
    la generazione, informare l'utente di quale azione stai per compiere su quale
    macchina e CHIEDERE ESPLICITAMENTE LA SUA AUTORIZZAZIONE.
    Non agire in modo distruttivo senza consenso.
    """
    proxmox = get_proxmox_client()
    action = action.lower()
    
    if action not in ["start", "stop", "reboot"]:
        return "Errore: Azione non supportata. Usa 'start', 'stop' o 'reboot'."
    
    try:
        if resource_type.lower() == "vm":
            api_path = proxmox.nodes(node).qemu(vm_id).status
        elif resource_type.lower() == "lxc":
            api_path = proxmox.nodes(node).lxc(vm_id).status
        else:
            return "Errore: 'resource_type' deve essere 'vm' o 'lxc'."
        
        # Invio dinamico del comando POST all'API
        if action == "start":
            api_path.start.post()
        elif action == "stop":
            api_path.stop.post()
        elif action == "reboot":
            api_path.reboot.post()
            
        return f"[Eseguito con successo su Proxmox]\nComando '{action}' inviato alla {resource_type.upper()} {vm_id}."
        
    except Exception as e:
        return f"Errore durante l'esecuzione dell'azione {action}: {str(e)}"
    

#UC3: Esecuzione di comandi arbitrari su istanze di virtualizzazione (implementato paradigma humain-in-the-loop)
@mcp.tool()
def execute_cmd(node: str, vm_id: int, command: str) -> str:
    """
    [ATTENZIONE: AZIONE CRITICA - HUMAN-IN-THE-LOOP RICHIESTO]
    Lancia comandi arbitrari sul terminale di un container LXC tramite accesso SSH al nodo.
    
    VINCOLO OPERATIVO OBBLIGATORIO:
    Prima di invocare questo tool, DEVI fermare la generazione, spiegare all'utente 
    quale comando esatto vuoi eseguire e PERCHÉ, e chiedere esplicitamente la sua 
    autorizzazione (es. "Posso procedere con l'esecuzione di 'rm -rf /tmp/*'?").
    NON ESEGUIRE MAI QUESTO TOOL SENZA IL CHIARO CONSENSO DELL'UTENTE.
    """
    host = os.environ.get("PROXMOX_HOST")
    password = os.environ.get("PROXMOX_SSH_PASSWORD")
    
    if not password:
        return "Errore: Variabile PROXMOX_SSH_PASSWORD mancante nella configurazione."

    try:
        # Inizializza il client SSH ignorando i certificati host sconosciuti
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connessione SSH al demone Proxmox
        ssh.connect(hostname=host, username='root', password=password, timeout=10)
        
        # pct exec lancia il comando direttamente all'interno dell'LXC
        comando_completo = f"pct exec {vm_id} -- {command}"
        
        stdin, stdout, stderr = ssh.exec_command(comando_completo)
        
        # Attesa della terminazione e lettura dei canali di output
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8').strip()
        err = stderr.read().decode('utf-8').strip()
        
        ssh.close()
        
        if exit_status != 0:
            return f"[Errore di esecuzione su LXC {vm_id}]\nExit code: {exit_status}\nErrore: {err}\nOutput: {out}"
        
        output_finale = out if out else "(Comando completato senza output visibile)"

        return f"[Eseguito con successo su Proxmox tramite SSH all'interno dell'LXC {vm_id}]\n\n{output_finale}"

    except Exception as e:
        return f"[Eseguito con successo su Proxmox tramite SSH all'interno dell'LXC {vm_id}]\n\n{output_finale}"

# Entry point
if __name__ == "__main__":
    mcp.run()