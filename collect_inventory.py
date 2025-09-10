import csv
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml


def make_session(username: str, password: str, verify_tls: bool = False, timeout: int = 15):
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({
        "Accept": "application/yang-data+json",
        "Content-Type": "application/yang-data+json",
    })
    s.verify = verify_tls
    s.timeout = timeout
    return s


def rc_get(session: requests.Session, host: str, relative_path: str):
    base = f"{host.rstrip('/')}/restconf/data/"
    url = base + relative_path  # IMPORTANT: don't treat YANG path as full URL
    try:
        r = session.get(url)
        if r.ok:
            try:
                return r.json(), r.status_code, None
            except ValueError:
                return None, r.status_code, "Invalid JSON"
        return None, r.status_code, r.text
    except requests.RequestException as e:
        return None, None, str(e)


def get_hostname(session, host):
    data, code, err = rc_get(session, host, "Cisco-IOS-XE-native:native/hostname")
    if data:
        for k, v in data.items():
            if "hostname" in k:
                return v
    return None


def get_version(session, host):
    data, code, err = rc_get(session, host, "Cisco-IOS-XE-native:native/version")
    if data:
        for k, v in data.items():
            if "version" in k:
                return v
    return None


def get_interfaces_summary(session, host):
    data, code, err = rc_get(session, host, "ietf-interfaces:interfaces")
    total = up = down = 0
    items = []

    if not data:
        return items, total, up, down

    root_key = next(iter(data))  # e.g., "ietf-interfaces:interfaces"
    iface_list = data[root_key].get("interface", [])

    for iface in iface_list:
        total += 1
        name = iface.get("name")
        enabled = iface.get("enabled")
        oper = iface.get("oper-status")
        if oper == "up":
            up += 1
        elif oper == "down":
            down += 1
        items.append({"name": name, "admin_enabled": enabled, "oper_status": oper})

    return items, total, up, down


def get_serial_number(session, host):
    candidates = [
        "Cisco-IOS-XE-device-hardware-oper:device-hardware-data/device-hardware/device-inventory",
        "Cisco-IOS-XE-device-hardware-oper:device-hardware-data/device-hardware/device-information",
    ]
    for p in candidates:
        data, code, err = rc_get(session, host, p)
        if not data:
            continue
        # Try inventory list
        inv = data.get("Cisco-IOS-XE-device-hardware-oper:device-inventory")
        if isinstance(inv, list):
            for item in inv:
                sn = item.get("serial-number") or item.get("serial")
                if sn:
                    return sn
        # Try device-information block
        info = data.get("Cisco-IOS-XE-device-hardware-oper:device-information")
        if isinstance(info, dict):
            sn = info.get("serial-number") or info.get("serial")
            if sn:
                return sn
    return None


def collect_for_device(dev):
    """
    dev = dict(host, username, password, name?, verify_tls?)
    returns (payload_dict, error_message_or_None)
    """
    name = dev.get("name") or dev["host"]
    host = dev["host"]
    user = dev["username"]
    pwd = dev["password"]
    verify_tls = bool(dev.get("verify_tls", False))

    session = make_session(user, pwd, verify_tls=verify_tls)

    payload = {
        "device_name": name,
        "host": host,
        "hostname": None,
        "version": None,
        "serial_number": None,
        "interfaces": [],
        "interfaces_total": 0,
        "interfaces_up": 0,
        "interfaces_down": 0,
        "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        payload["hostname"] = get_hostname(session, host)
        payload["version"] = get_version(session, host)

        ifaces, total, up, down = get_interfaces_summary(session, host)
        payload["interfaces"] = ifaces
        payload["interfaces_total"] = total
        payload["interfaces_up"] = up
        payload["interfaces_down"] = down

        payload["serial_number"] = get_serial_number(session, host)

        return payload, None
    except Exception as e:
        return payload, str(e)


def main():
    Path("output").mkdir(parents=True, exist_ok=True)

    # Load devices.yaml
    with open("devices.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    devices = cfg.get("devices", [])

    ts = time.strftime("%Y%m%d_%H%M%S")
    csv_path = Path("output") / f"inventory_{ts}.csv"

    # Prepare CSV
    fieldnames = [
        "device_name", "host", "hostname", "version", "serial_number",
        "interfaces_total", "interfaces_up", "interfaces_down",
        "collected_at", "status", "error"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.DictWriter(csvf, fieldnames=fieldnames)
        writer.writeheader()

        for dev in devices:
            payload, err = collect_for_device(dev)

            # Save per-device JSON
            safe_name = (payload["device_name"] or "device").replace("://", "_").replace(":", "_").replace("/", "_")
            json_path = Path("output") / f"{safe_name}_{ts}.json"
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(payload, jf, indent=2, ensure_ascii=False)

            # Write CSV row
            row = {k: payload.get(k) for k in fieldnames if k in payload}
            row["status"] = "ok" if err is None else "error"
            row["error"] = "" if err is None else err
            writer.writerow(row)

            print(f"[OK] {payload['device_name']} -> JSON: {json_path.name}")

    print(f"[DONE] Inventory CSV: {csv_path}")


if __name__ == "__main__":
    main()
