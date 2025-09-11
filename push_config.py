import argparse
import json
import time
from pathlib import Path

import requests
import yaml
from jinja2 import Environment, FileSystemLoader
from requests.auth import HTTPBasicAuth


# ---------- Common ----------
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

def rc_get(sess, host, path):
    url = f"{host.rstrip('/')}/restconf/data/{path}"
    r = sess.get(url)
    body = {}
    try:
        if r.content:
            body = r.json()
    except Exception:
        body = {"_raw": r.text}
    return r.status_code, body

# ---------- Native (hostname, domain, banner, ntp) ----------
def build_native_payload(intent: dict):
    body = {"Cisco-IOS-XE-native:native": {}}
    sys = intent.get("system", {})
    ntp = intent.get("ntp", {})

    if sys.get("hostname"):
        body["Cisco-IOS-XE-native:native"]["hostname"] = sys["hostname"]

    if sys.get("domain_name"):
        body["Cisco-IOS-XE-native:native"].setdefault("ip", {})
        body["Cisco-IOS-XE-native:native"]["ip"].setdefault("domain", {})
        body["Cisco-IOS-XE-native:native"]["ip"]["domain"]["name"] = sys["domain_name"]

    if sys.get("banner_motd"):
        body["Cisco-IOS-XE-native:native"].setdefault("banner", {})
        body["Cisco-IOS-XE-native:native"]["banner"]["motd"] = {
            "banner": sys["banner_motd"]
        }

    servers = ntp.get("servers", []) or []
    if servers:
        body["Cisco-IOS-XE-native:native"]["ntp"] = {
            "server": [{"ip-address": ip} for ip in servers]
        }

    return body

def restconf_patch_native(session, host, native_payload):
    url = f"{host.rstrip('/')}/restconf/data/Cisco-IOS-XE-native:native"
    return session.patch(url, data=json.dumps(native_payload))

# ---------- IETF interfaces (Loopbacks) ----------
def build_ietf_loopback_payload(lb):
    return {
        "ietf-interfaces:interface": {
            "name": f"Loopback{lb['name']}",
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {
                "address": [
                    {"ip": str(lb["ip"]), "netmask": str(lb["mask"])}
                ]
            }
        }
    }

def restconf_put_interface(session, host, if_name, payload):
    url = f"{host.rstrip('/')}/restconf/data/ietf-interfaces:interfaces/interface={if_name}"
    return session.put(url, data=json.dumps(payload))

# ---------- Checks (intent vs device) ----------
def check_hostname(sess, host, intent_hostname):
    code, body = rc_get(sess, host, "Cisco-IOS-XE-native:native/hostname")
    actual = None
    if code == 200:
        # {"Cisco-IOS-XE-native:hostname": "VALUE"}
        actual = next(iter(body.values()))
    result = {
        "item": "hostname",
        "intent": intent_hostname,
        "actual": actual,
        "http": code,
        "match": (intent_hostname == actual)
    }
    return result

def check_loopbacks(sess, host, intent_loopbacks):
    results = []
    for lb in intent_loopbacks or []:
        name = f"Loopback{lb['name']}"
        code, body = rc_get(sess, host, f"ietf-interfaces:interfaces/interface={name}")
        actual_ip = None
        if code == 200:
            try:
                iface = body.get("ietf-interfaces:interface", {})
                addrs = iface.get("ietf-ip:ipv4", {}).get("address", [])
                if addrs:
                    actual_ip = addrs[0].get("ip")
            except Exception:
                pass
        results.append({
            "item": f"interface-{name}",
            "intent": lb["ip"],
            "actual": actual_ip,
            "http": code,
            "match": (lb["ip"] == actual_ip)
        })
    return results

# ---------- Rendering ----------
def render_config(template_path, intent):
    env = Environment(loader=FileSystemLoader("templates"), trim_blocks=True, lstrip_blocks=True)
    tpl = env.get_template(Path(template_path).name)
    return tpl.render(**intent)

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Render configs from intent; apply and/or check device state.")
    parser.add_argument("--intent", required=True, help="Path to intent YAML (e.g., intents/site1.yaml)")
    parser.add_argument("--template", required=True, help="Path to Jinja2 template (e.g., templates/base_config.j2)")
    parser.add_argument("--devices", default="devices.yaml", help="Path to devices.yaml (local, ignored by git)")
    parser.add_argument("--apply", action="store_true", help="Apply changes via RESTCONF")
    parser.add_argument("--check", action="store_true", help="Compare intent vs device and produce a diff report")
    args = parser.parse_args()

    if not args.apply and not args.check:
        print("[INFO] No --apply/--check flags provided; doing a render-only dry run.")

    intent = load_yaml(args.intent)
    devices_cfg = load_yaml(args.devices)
    devices = devices_cfg.get("devices", [])
    if not devices:
        raise SystemExit("No devices found in devices.yaml")

    Path("output").mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    label = Path(args.intent).stem

    # Render once (same for all)
    rendered = render_config(args.template, intent)
    rendered_path = Path("output") / f"{label}_rendered_{ts}.txt"
    rendered_path.write_text(rendered, encoding="utf-8")
    print(f"[OK] Rendered config -> {rendered_path}")

    native_payload = build_native_payload(intent)
    lbs = intent.get("loopbacks", []) or []

    overall_results = []

    for dev in devices:
        name = dev.get("name") or dev["host"]
        host = dev["host"]
        user = dev["username"]
        pwd = dev["password"]
        verify_tls = bool(dev.get("verify_tls", False))
        status = {"device_name": name, "host": host, "steps": [], "checks": []}

        sess = make_session(user, pwd, verify=verify_tls)

        # APPLY
        if args.apply:
            if native_payload["Cisco-IOS-XE-native:native"]:
                r = restconf_patch_native(sess, host, native_payload)
                status["steps"].append(
                    {"op": "native-patch", "http": r.status_code, "ok": r.ok, "err": None if r.ok else r.text}
                )
            for lb in lbs:
                if_name = f"Loopback{lb['name']}"
                payload = build_ietf_loopback_payload(lb)
                r = restconf_put_interface(sess, host, if_name, payload)
                status["steps"].append(
                    {"op": f"put-{if_name}", "http": r.status_code, "ok": r.ok, "err": None if r.ok else r.text}
                )
        else:
            status["steps"].append({"op": "dry-run", "http": None, "ok": True, "err": None})

        # CHECK
        if args.check:
            sys = intent.get("system", {})
            status["checks"].append(check_hostname(sess, host, sys.get("hostname")))
            status["checks"].extend(check_loopbacks(sess, host, lbs))

        overall_results.append(status)
        print(f"[INFO] {name}: steps={status['steps']}{' checks='+str(status['checks']) if args.check else ''}")

    # Save summary
    summary = {"intent": intent, "results": overall_results, "mode": {"apply": args.apply, "check": args.check}}
    summary_path = Path("output") / f"{label}_summary_{ts}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[OK] Summary -> {summary_path}")

if __name__ == "__main__":
    main()
