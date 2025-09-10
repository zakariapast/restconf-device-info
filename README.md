# RESTCONF Network Automation Portfolio

This repository demonstrates a progressive **network automation portfolio** using Cisco DevNet Sandboxes, RESTCONF, Python, and related tools.

Each step builds on the previous one, moving from data collection → multi-device inventory → configuration automation.

---

## 📍 Step 1 — Device Info Collector

A simple Python script that connects to a Cisco IOS-XE sandbox using **RESTCONF**, collects device information, and saves the results as JSON.

### Features

* Connects to Cisco IOS-XE device via RESTCONF
* Collects:

  * Hostname
  * Software version
  * Serial number (if available)
  * Interfaces (name, admin state, operational status)
* Saves output to timestamped JSON file under `output/`

### Run

```bash
python collect_device_info.py
```

Output example:

```json
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
```

---

## 📍 Step 2 — Multi-Device Inventory (CSV Export)

Expands Step 1 into a **multi-device collector** that loops across multiple devices and produces both JSON and consolidated CSV reports.

### Features

* Read device connection details from `devices.yaml`
* Collect hostname, version, serial number, interface counts
* Save one JSON per device in `output/`
* Save one consolidated CSV report (timestamped)

### Example CSV Columns

```
device_name, host, hostname, version, serial_number,
interfaces_total, interfaces_up, interfaces_down,
collected_at, status, error
```

### Usage

```bash
python collect_inventory.py
```

### Important Notes

* Do **NOT** commit `devices.yaml` with real credentials.
* Instead, use `devices.example.yaml` as a safe template:

```yaml
devices:
  - name: iosxe-1
    host: "https://sandbox-iosxe-latest-1.cisco.com:443"
    username: "developer"
    password: "your-password-here"
    verify_tls: false
```

---

## 📍 Step 3 — Configuration Automation with Jinja2 + RESTCONF

Move from **read-only inventory** to **configuration automation** by describing intent in YAML, rendering configs with Jinja2 templates, and pushing them via RESTCONF.

### Project Structure

```
restconf-device-info/
├─ templates/
│   └─ base_config.j2         # Jinja2 template for device configs
├─ intents/
│   └─ site1.yaml             # Intent file describing VLANs, OSPF, etc.
├─ push_config.py             # Python script to render + push configs
├─ collect_device_info.py     # Step 1 script
├─ collect_inventory.py       # Step 2 script
├─ devices.example.yaml       # Device connection details (safe example)
├─ requirements.txt           # Updated with Jinja2
└─ README.md                  # Documentation
```

### Example Intent (`intents/site1.yaml`)

```yaml
vlans:
  - id: 10
    name: Users
  - id: 20
    name: Voice

ospf:
  process_id: 1
  networks:
    - { network: "10.10.10.0/24", area: 0 }
    - { network: "10.20.20.0/24", area: 0 }
```

### Example Template (`templates/base_config.j2`)

```jinja
! VLAN Configuration
{% for vlan in vlans %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% endfor %}

! OSPF Configuration
router ospf {{ ospf.process_id }}
{% for net in ospf.networks %}
 network {{ net.network }} area {{ net.area }}
{% endfor %}
```

### Requirements

Add Jinja2 to `requirements.txt`:

```
requests
python-dotenv
PyYAML
Jinja2
```

Install with:

```bash
pip install -r requirements.txt
```

### Usage

```bash
python push_config.py --intent intents/site1.yaml --template templates/base_config.j2
```

### Output

* `output/site1_rendered.txt` → the generated CLI config
* `output/site1_response.json` → RESTCONF API response

---

## 📌 Roadmap

* Step 4: Meraki Dashboard API automation
* Step 5: Orchestration with Ansible
* Step 6: Telemetry + Monitoring
