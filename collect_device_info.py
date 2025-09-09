import os
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()

HOST = os.getenv("DEVICE_HOST", "").rstrip("/")
USER = os.getenv("DEVICE_USER")
PASS = os.getenv("DEVICE_PASS")

# RESTCONF headers (YANG JSON)
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}

# In lab/sandbox we usually skip TLS verification due to self-signed certs.
# DO NOT do this in production.
VERIFY_TLS = False

session = requests.Session()
session.auth = (USER, PASS)
session.headers.update(HEADERS)
session.verify = VERIFY_TLS
session.timeout = 15  # seconds


def rc_get(relative_path: str):
    base = f"{HOST}/restconf/data/"
    # Ensure we are always hitting HOST + /restconf/data/<path>
    url = base + relative_path

    try:
        r = session.get(url)
        if r.ok:
            try:
                return r.json(), r.status_code
            except ValueError:
                return None, r.status_code
        else:
            return None, r.status_code
    except requests.RequestException as e:
        print(f"[ERROR] GET {relative_path}: {e}")
        return None, None


def get_hostname():
    # IOS-XE native hostname
    paths = [
        "Cisco-IOS-XE-native:native/hostname",
    ]
    for p in paths:
        data, code = rc_get(p)
        if data:
            # The key may appear as "Cisco-IOS-XE-native:hostname"
            for k, v in data.items():
                if "hostname" in k:
                    return v
    return None


def get_version():
    # Try multiple models; availability varies by image
    paths = [
        "Cisco-IOS-XE-native:native/version",
        # Some images expose platform info under different trees; keep it simple here.
    ]
    for p in paths:
        data, code = rc_get(p)
        if data:
            for k, v in data.items():
                if "version" in k:
                    return v
    return None


def get_interfaces_summary():
    """
    Return a list of dicts: [{name, enabled (admin), oper-status}, ...]
    """
    # ietf-interfaces is widely available
    data, code = rc_get("ietf-interfaces:interfaces")
    interfaces = []

    if not data:
        return interfaces

    # Expect something like:
    # { "ietf-interfaces:interfaces": { "interface": [ {...}, {...} ] } }
    root_key = next(iter(data))
    iface_list = data[root_key].get("interface", [])

    for iface in iface_list:
        name = iface.get("name")
        enabled = iface.get("enabled")
        # Oper status sometimes lives in a separate operational state tree.
        # Many sandboxes also include it here as "oper-status".
        oper = iface.get("oper-status")
        interfaces.append(
            {"name": name, "admin_enabled": enabled, "oper_status": oper}
        )
    return interfaces


def get_serial_number():
    """
    Try to fetch serial number via device-hardware YANG (may not exist on all images).
    Returns a string or None.
    """
    candidates = [
        # Inventory list
        "Cisco-IOS-XE-device-hardware-oper:device-hardware-data/device-hardware/device-inventory",
        # Device information block
        "Cisco-IOS-XE-device-hardware-oper:device-hardware-data/device-hardware/device-information",
    ]
    for p in candidates:
        data, code = rc_get(p)
        if not data:
            continue
        # Heuristic search for 'serial' fields
        json_text = json.dumps(data).lower()
        if "serial" in json_text:
            # Try a few common shapes:
            inv = data.get("Cisco-IOS-XE-device-hardware-oper:device-inventory")
            if isinstance(inv, list):
                for item in inv:
                    sn = item.get("serial-number") or item.get("serial")
                    if sn:
                        return sn
            info = data.get("Cisco-IOS-XE-device-hardware-oper:device-information")
            if isinstance(info, dict):
                sn = info.get("serial-number") or info.get("serial")
                if sn:
                    return sn
    return None


def main():
    if not (HOST and USER and PASS):
        raise SystemExit("Please set DEVICE_HOST, DEVICE_USER, DEVICE_PASS in .env")

    payload = {
        "host": HOST,
        "hostname": get_hostname(),
        "version": get_version(),
        "serial_number": get_serial_number(),
        "interfaces": get_interfaces_summary(),
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Save to output/
    Path("output").mkdir(parents=True, exist_ok=True)
    safe_host = HOST.replace("https://", "").replace("http://", "").replace(":", "_").replace("/", "_")
    out_path = Path("output") / f"device_{safe_host}_{int(time.time())}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved: {out_path}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
