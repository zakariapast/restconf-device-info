import os, time, yaml, json
from pathlib import Path
from dotenv import load_dotenv
import meraki

load_dotenv()
API_KEY = os.getenv("MERAKI_API_KEY") or ""
if not API_KEY: raise SystemExit("Set MERAKI_API_KEY in .env")

dash = meraki.DashboardAPI(API_KEY, suppress_logging=True, maximum_retries=5)

def find_ids(org_name, net_name):
  orgs = dash.organizations.getOrganizations()
  org = next((o for o in orgs if o["name"] == org_name), None)
  if not org: raise SystemExit(f"Org '{org_name}' not found")
  nets = dash.organizations.getOrganizationNetworks(org["id"])
  net = next((n for n in nets if n["name"] == net_name), None)
  if not net: raise SystemExit(f"Network '{net_name}' not found in org '{org_name}'")
  return org["id"], net["id"]

def main():
  intent = yaml.safe_load(open("intents/meraki_wifi.yaml", encoding="utf-8"))
  org_name = intent["target"]["organization_name"]
  net_name = intent["target"]["network_name"]
  ssid_spec = intent["ssid"]; number = ssid_spec["number"]

  org_id, net_id = find_ids(org_name, net_name)

  # Current state (GET)
  current = dash.wireless.getNetworkWirelessSsid(net_id, number)

  # Desired state (subset we will manage)
  desired = {
      "name": ssid_spec["name"],
      "enabled": ssid_spec["enabled"],
      "authMode": ssid_spec["authMode"],
      "psk": ssid_spec.get("psk"),
      "ipAssignmentMode": ssid_spec.get("ipAssignmentMode")
  }

  # Produce a minimal diff
  changes = {k: v for k, v in desired.items() if current.get(k) != v}

  Path("output").mkdir(exist_ok=True)
  ts = time.strftime("%Y%m%d_%H%M%S")
  (Path("output")/f"meraki_ssid_diff_{ts}.json").write_text(
      json.dumps({"org":org_name,"network":net_name,"number":number,
                  "current":current, "desired":desired, "changes":changes}, indent=2),
      encoding="utf-8"
  )
  print(f"[OK] Wrote diff to output/meraki_ssid_diff_{ts}.json")

  # Try to APPLY; handle 403 nicely
  try:
      if changes:
          resp = dash.wireless.updateNetworkWirelessSsid(net_id, number, **{k:v for k,v in changes.items() if v is not None})
          print("[OK] Updated SSID:", resp["name"])
      else:
          print("[OK] No changes needed; already matches intent.")
  except meraki.APIError as e:
      if e.status == 403:
          print("[WARN] 403 Forbidden: your API key is read-only for this org/network. Keeping diff-only output.")
      else:
          raise

if __name__ == "__main__":
  main()