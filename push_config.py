import argparse
import json
import time
from pathlib import Path

import requests
import yaml
from jinja2 import Environment, FileSystemLoader

# ---------- Helpers ----------
def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def make_session(username, password, verify=False, timeout=20):
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({
        "Accept": "application/yang-data+json",
        "Content-Type": "application/yang-data+json",
    })
    s.verify = verify
    s.timeout = timeout
    return s

def restconf_patch_native(session, host, native_payload):
    """
    PATCH to /restconf/data/Cisco-IOS-XE-native:native
    Example native_payload: {"Cisco-IOS-XE-native:native": {"hostname": "BRANCH1-DEMO"}}
    """
    base = f"{host.rstrip('/')}/restconf/data/Cisco-IOS-XE-native:native"
    r = session.patch(base, data=json.dumps(native_payload))
    return r

# ---------- Intent → payloads ----------
def build_native_payload(intent: dict):
    """
    For safety and demo, we only push 'hostname' via RESTCONF.
    Extend later for banners, NTP, etc.
    """
    payload = {"Cisco-IOS-XE-native:native": {}}
    if intent.get("hostname"):
        payload["Cisco-IOS-XE-native:native"]["hostname"] = intent["hostname"]
    return payload

# ---------- Rendering ----------
def render_config(template_path, intent):
    env = Environment(loader=FileSystemLoader("templates"), trim_blocks=True, lstrip_blocks=True)
    tpl = env.get_template(Path(template_path).name)
    return tpl.render(**intent)

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Render (and optionally push) configs from intent.")
    parser.add_argument("--intent", required=True, help="Path to intent YAML (e.g., intents/site1.yaml)")
    parser.add_argument("--template", required=True, help="Path to Jinja2 template (e.g., templates/base_config.j2)")
    parser.add_argument("--devices", default="devices.yaml", help="Path to devices.yaml (local, ignored from git)")
    parser.add_argument("--apply", action="store_true", help="Apply changes via RESTCONF (hostname only, safe demo)")
    args = parser.parse_args()

    # Load inputs
    intent = load_yaml(args.intent)
    devices_cfg = load_yaml(args.devices)
    devices = devices_cfg.get("devices", [])
    if not devices:
        raise SystemExit("No devices found in devices.yaml")

    # Output folder
    Path("output").mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    label = Path(args.intent).stem

    # Render once (the same template for all)
    rendered = render_config(args.template, intent)
    rendered_path = Path("output") / f"{label}_rendered_{ts}.txt"
    rendered_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] Rendered config -> {rendered_path}")

    # Build RESTCONF payload (hostname only for now)
    native_payload = build_native_payload(intent)

    # Optionally apply
    results = []
    for dev in devices:
        name = dev.get("name") or dev["host"]
        host = dev["host"]
        user = dev["username"]
        pwd = dev["password"]
        verify_tls = bool(dev.get("verify_tls", False))

        status = {"device_name": name, "host": host, "applied": False, "http_status": None, "error": None}

        if args.apply and native_payload["Cisco-IOS-XE-native:native"]:
            try:
                sess = make_session(user, pwd, verify=verify_tls)
                resp = restconf_patch_native(sess, host, native_payload)
                status["http_status"] = resp.status_code
                if resp.ok:
                    status["applied"] = True
                else:
                    status["error"] = resp.text
            except requests.RequestException as e:
                status["error"] = str(e)

        results.append(status)
        print(f"[INFO] {name}: apply={status['applied']} http={status['http_status']} err={status['error']}")

    # Save outcome
    summary_path = Path("output") / f"{label}_push_summary_{ts}.json"
    summary_path.write_text(json.dumps({"intent": intent, "results": results}, indent=2), encoding="utf-8")
    print(f"[OK] Summary -> {summary_path}")

if __name__ == "__main__":
    main()
