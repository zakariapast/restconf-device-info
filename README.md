# Network Automation Portfolio

This repository showcases a hands-on portfolio of **network automation** using Cisco DevNet sandboxes, Python, and GitHub Actions CI/CD.

---

## Step 1 — RESTCONF Device Info Collector (Cisco IOS-XE)

**What it does**

* Connects to IOS‑XE DevNet sandbox via RESTCONF and collects facts (hostname, version, serial, interfaces).
* Saves structured JSON under `/output/`.

**Key files**

* `collect_device_info.py`
* `.env.example` (copy to `.env` locally)
* `requirements.txt`

**Run**

```bash
python collect_device_info.py
```

**Output (example)**

```json
{
  "host": "https://sandbox-iosxe-latest-1.cisco.com:443",
  "hostname": "BRANCH1-DEMO",
  "version": "17.x",
  "serial_number": "...",
  "interfaces": ["GigabitEthernet1", "Loopback100"],
  "collected_at": "2025-09-09T18:11:48"
}
```

---

## Step 2 — Multi-Device Inventory + CSV Export

**What it does**

* Polls **multiple devices** listed in a YAML inventory.
* Writes one JSON per device **and** a consolidated CSV report.

**Key files**

* `collect_inventory.py`
* `devices.example.yaml` (copy to `devices.yaml` locally; **never commit secrets**)

**Run**

```bash
python collect_inventory.py
```

**Output**

* `output/inventory_*.csv` (tabular report)
* `output/device_*.json` per device

---

## Step 3 — Configuration Push with Jinja2 + RESTCONF

**What it does**

* Describes desired state in **intent YAML** and renders human‑readable config with **Jinja2**.
* Pushes safe changes via RESTCONF (tested: hostname + loopbacks using IETF interfaces model).
* `--check` mode compares **intent vs device** and generates a mini diff report (JSON).

**Key files**

* `intents/site1.yaml` (intent)
* `templates/base_config.j2` (Jinja2 template)
* `push_config.py` (supports `--apply`, `--check`)
* `verify_all.py` (single verify for hostname + loopbacks)

**Common commands**

```bash
# Render only
python push_config.py --intent intents/site1.yaml --template templates/base_config.j2

# Render + apply + check
python push_config.py --intent intents/site1.yaml --template templates/base_config.j2 --apply --check

# Verify via RESTCONF (example)
curl.exe -k -u developer:C1sco12345 -H "Accept: application/yang-data+json" \
  https://sandbox-iosxe-latest-1.cisco.com:443/restconf/data/Cisco-IOS-XE-native:native/hostname
```

**Output**

* `output/site1_rendered_*.txt` (rendered CLI)
* `output/site1_summary_*.json` (steps + checks)

> Note: Some native subtrees (banner/domain/NTP) are not exposed on the Always‑On sandbox; the code handles that gracefully.

---

## Step 4 — Meraki Dashboard API (Read‑Only Sandbox)

**What it does**

* Uses Meraki API to export **organizations/networks/devices** into CSVs.
* Defines SSID intent in YAML and produces a **diff JSON** against live Dashboard. (Writes are blocked on public sandbox → handled as warning.)

**Key files**

* `meraki_collect.py` (orgs/networks/devices → CSV)
* `meraki_config.py` (intent → diff; catches 403 Forbidden)
* `verify_meraki.py` (read back SSID properties)
* `intents/meraki_wifi.yaml` (intent)

**Run**

```bash
# Inventory
python meraki_collect.py

# Plan (intent → diff)
python meraki_config.py

# Verify
python verify_meraki.py
```

**Output**

* `output/meraki_orgs_*.csv`, `output/meraki_networks_*.csv`, `output/meraki_devices_*.csv`
* `output/meraki_ssid_diff_*.json`

> Note: DevNet Meraki Always‑On is read‑only; diffs are produced, apply is skipped.

---

## Step 5 — CI/CD with GitHub Actions ✅

**What it does**

* Runs automatically on push/PR and weekly schedule.
* Builds a clean artifact bundle for recruiters: IOS‑XE checks, Meraki CSVs, Meraki diff.
* Secrets are injected at runtime via GitHub **Actions Secrets** (`IOSXE_HOST`, `IOSXE_USER`, `IOSXE_PASS`, `MERAKI_API_KEY`).
* Steps are tolerant of sandbox quirks to keep the badge green.

**Key files**

* `.github/workflows/portfolio-ci.yml`

**What the workflow runs**

1. Create ephemeral `devices.yaml` from secrets.
2. IOS‑XE: `push_config.py --check` (no apply in CI).
3. Meraki: `meraki_collect.py` and `meraki_config.py` (diff‑only).
4. Upload `/output/**` as the **automation-results** artifact.

**Badge**

![CI](https://github.com/zakariapast/restconf-device-info/actions/workflows/portfolio-ci.yml/badge.svg)

---

## Repo Hygiene

* `.env` and `devices.yaml` are excluded via `.gitignore`.
* Example files provided: `.env.example`, `devices.example.yaml`.
* Artifacts and secrets are not committed.

---

### How to Run Locally

```bash
# Clone repo
git clone https://github.com/zakariapast/restconf-device-info.git
cd restconf-device-info

# Virtual env
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Multi-device inventory (Step 2)
python collect_inventory.py

# Render + apply + check (Step 3)
python push_config.py --intent intents/site1.yaml --template templates/base_config.j2 --apply --check

# Meraki (Step 4)
python meraki_collect.py
python meraki_config.py
python verify_meraki.py
```

---

This project demonstrates **end‑to‑end network automation**: device discovery, inventory reporting, intent‑based configuration, multi‑vendor API integration, and CI/CD validation.
