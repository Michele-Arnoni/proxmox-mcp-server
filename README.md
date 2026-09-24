# Proxmox MCP Server

A Model Context Protocol (MCP) server that acts as a bridge between Large Language Models (e.g., Claude) and a Proxmox VE hypervisor. 
Developed as a Proof of Concept (PoC) for a university thesis, this project focuses on AI-driven infrastructure orchestration with a strong emphasis on **Human-in-the-Loop** safety patterns.

## Tech Stack
- **Python 3.11+**
- `mcp` (Official Model Context Protocol SDK v2.x)
- `proxmoxer` (REST client for Proxmox API)

## Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Michele-Arnoni/proxmox-mcp-server.git](https://github.com/Michele-Arnoni/proxmox-mcp-server.git)
   cd proxmox-mcp-server

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux/macOS

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

5. **Configuration:**
   For security reasons, the server reads the Proxmox credentials from environment variables. Never hardcode credentials or tokens in the source code.
  * Generate a Proxmox API Token
    * Log in to your Proxmox Web GUI.
    * Navigate to Datacenter > Permissions > API Tokens.
    * Click Add to create a new token for your user (e.g., root@pam). Uncheck "Privilege Separation" for full user rights.
    * Copy the Secret Value immediately (it will only be shown once).

  * Configure Claude Desktop (MCP Client)
    * Update your Claude Desktop configuration file (on Linux/AUR this is usually located at ~/.config/Claude/claude_desktop_config.json) by adding the following server block:
     ```json
     {
      "mcpServers": {
        "proxmox-middleware": {
          "command": "/ABSOLUTE/PATH/TO/YOUR/PROJECT/venv/bin/python",
          "args": [
            "/ABSOLUTE/PATH/TO/YOUR/PROJECT/mcpserver.py"
          ],
          "env": {
            "PROXMOX_HOST": "192.168.x.x",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_TOKEN_NAME": "YOUR_TOKEN_NAME",
            "PROXMOX_TOKEN_VALUE": "YOUR_TOKEN_SECRET"
          }
        }
      }
    }

  Note: Ensure you use absolute paths for both the Python executable in your virtual environment and the mcpserver.py script.
  
7. **Available Tools:**
   * list_vms: Inspects the Proxmox node and retrieves a list of all Virtual Machines (QEMU) and Containers (LXC), including their IDs, names, and current power status.
   * manage_vm_state: Manages the Proxmox instances life cycle, using "start", "reboot" and "stop" commands.
   * clone_resource: Create a Proxmox instance from another, cloning it.
   * destroy_resource: Destroy a Proxmox instance.
   * execute_cmd: Execute whatever CLI command on a node by SSHv2.
