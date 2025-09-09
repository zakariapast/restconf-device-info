# RESTCONF Device Info Collector

A simple Python project that connects to a Cisco IOS-XE sandbox using **RESTCONF**, collects device information, and saves the results as JSON.

This is part of my **Network Automation Portfolio**.

---

## Features
- Connects to Cisco IOS-XE device via RESTCONF
- Collects:
  - Hostname
  - Software version
  - Serial number (if available)
  - Interfaces (name, admin state, operational status)
- Saves output to timestamped JSON file under `output/`

---

## Requirements
- Python 3.8+
- Virtual environment (recommended)

```bash
pip install -r requirements.txt
Setup

Clone this repository

git clone https://github.com/zakariapast/restconf-device-info.git
cd restconf-device-info


Create a virtual environment

python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # Linux/macOS


Install dependencies

pip install -r requirements.txt


Create a .env file in the project root:

DEVICE_HOST=https://sandbox-iosxe-latest-1.cisco.com:443
DEVICE_USER=developer
DEVICE_PASS=C1sco12345


Run the collector

python collect_device_info.py

Example Output
{
  "host": "https://sandbox-iosxe-latest-1.cisco.com:443",
  "hostname": "ios-xe-mgmt",
  "version": "17.9.1a",
  "serial_number": "9Z123ABC456",
  "interfaces": [
    {"name": "GigabitEthernet1", "admin_enabled": true, "oper_status": "up"},
    {"name": "Loopback0", "admin_enabled": true, "oper_status": "up"}
  ],
  "collected_at": "2025-09-09 18:30:12"
}

Notes

This project uses Cisco DevNet Always-On Sandbox
.

Self-signed certs are ignored (verify=False) for sandbox use only.

Do not commit .env or real credentials to Git.

Next Steps

This is Step 1 of a bigger roadmap:

Step 2: Collect inventory from multiple devices → save as CSV/Excel

Step 3: Automate configuration with Jinja2 templates

Step 4: Cloud API automation (Cisco Meraki Dashboard)

Step 5: Orchestration with Ansible


---

👉 Suggestion: Add this as `README.md` in your repo, commit, and push.  
Then we can continue to **Step 2 (multi-device inventory + CSV export)**.  

Do you want me to scaffold Step 2 now (with a `devices.yaml` and CSV writer), or finish polishing Step 1 first
