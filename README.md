# Network Automation Portfolio

This repository contains step-by-step labs demonstrating **network automation** using Cisco DevNet sandboxes, RESTCONF (IOS-XE), and Meraki Dashboard API.

Each step builds on the previous one, showing how to go from simple device info collection to intent-driven configuration management and multi-vendor workflows.

---

## Step 1 — RESTCONF Device Info Collector

* Connect to **Cisco IOS-XE Always-On Sandbox**
* Use Python `requests` + RESTCONF to collect device facts
* Store results as JSON files in `output/`

**Key files:**

* `collect_device_info.py`
* `.env.example`
* `requirements.txt`

**Run:**

```bash
python collect_device_info.py
```

**Example Output:**

```json
{
  "host": "https://devnetsandboxiosxe.cisco.com:443",
  "hostname": "ios-xe-mgmt.cisco.com",
  "version": "17.9.1a",
  "serial_number": "ABC12345",
  "interfaces": ["GigabitEthernet1", "Loopback0"],
  "collected_at": "2025-09-09T18:11:48"
}
```

---

## Step 2 — Multi-Device Inventory + CSV Export

* Support multiple devices via `devices.yaml`
* Export collected info into a CSV for reporting

**Key files:**

* `collect_inventory.py`
* `devices.example.yaml`

**Run:**

```bash
python collect_inventory.py
```

**Example CSV:**

```csv
hostname,version,serial_number
CSR1kv-1,17.9.1a,ABCD1234
CSR1kv-2,17.9.1a,EFGH5678
```

---

## Step 3 — Jinja2 Templates + RESTCONF Config Push

* Define **intent YAML** (desired state)
* Render configs using **Jinja2 templates**
* Push hostname + loopback interfaces via RESTCONF
* Add `--check` mode: verify intent vs. device state (mini diff)

**Key files:**

* `intents/site1.yaml`
* `templates/base_config.j2`
* `push_config.py` (supports `--apply` and `--check`)
* `verify_all.py`

**Render only:**

```bash
python push_config.py --intent intents/site1.yaml --template templates/base_config.j2
```

**Render + Apply + Check:**

```bash
python push_config.py --intent intents/site1.yaml --template templates/base_config.j2 --apply --check
```

**Verify RESTCONF directly:**

```bash
curl -k -u developer:C1sco12345 \
  -H "Accept: application/yang-data+json" \
  https://sandbox-iosxe-latest-1.cisco.com:443/restconf/data/Cisco-IOS-XE-native:native/hostname
```

**Example diff summary (JSON):**

```json
{
  "item": "hostname",
  "intent": "BRANCH1-DEMO",
  "actual": "BRANCH1-DEMO",
  "match": true
}
```

---

## Step 4 — Meraki Dashboard API (Read-Only Sandbox)

* Use **Meraki Always-On Sandbox**
* Collect orgs/networks/devices into CSV
* Define **intent YAML** for SSID configuration
* Generate a **diff JSON** (intent vs. actual) — sandbox is read-only so no writes allowed
* Verify current SSID settings via API

**Key files:**

* `meraki_collect.py` → export orgs, networks, devices
* `meraki_config.py` → intent-to-diff (gracefully handles 403 Forbidden)
* `verify_meraki.py` → read back SSID config
* `intents/meraki_wifi.yaml`

**Collect inventory:**

```bash
python meraki_collect.py
```

**Plan (intent → diff):**

```bash
python meraki_config.py
```

**Verify:**

```bash
python verify_meraki.py
```

**Example diff output:**

```json
{
  "org": "DevNet Sandbox",
  "network": "DevNet Sandbox ALWAYS ON",
  "number": 7,
  "changes": {
    "name": "Portfolio-Demo",
    "psk": "Portf0lio-Wifi!"
  },
  "note": "403 Forbidden on sandbox (read-only). Changes not applied."
}
```

---

## Next Steps

* Step 5: Orchestration with Ansible or GitHub Actions (infra-as-code pipeline)
* Add rollback functionality for IOS-XE configs
* Polish README with screenshots of JSON/CSV/verification results
