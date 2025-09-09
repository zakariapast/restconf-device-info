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
