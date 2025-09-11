import os, yaml
from dotenv import load_dotenv
import meraki

load_dotenv()
api_key = os.getenv("MERAKI_API_KEY")
dash = meraki.DashboardAPI(api_key, suppress_logging=True, maximum_retries=5)

intent = yaml.safe_load(open("intents/meraki_wifi.yaml", "r", encoding="utf-8"))
org_name = intent["target"]["organization_name"]
net_name = intent["target"]["network_name"]
number   = intent["ssid"]["number"]

def find_ids():
    orgs = dash.organizations.getOrganizations()
    org = next(o for o in orgs if o["name"] == org_name)
    nets = dash.organizations.getOrganizationNetworks(org["id"])
    net = next(n for n in nets if n["name"] == net_name)
    return org["id"], net["id"]

def main():
    org_id, net_id = find_ids()
    ssid = dash.wireless.getNetworkWirelessSsid(net_id, number)
    print({
        "org": org_name,
        "network": net_name,
        "number": number,
        "name": ssid.get("name"),
        "enabled": ssid.get("enabled"),
        "authMode": ssid.get("authMode"),
        "ipAssignmentMode": ssid.get("ipAssignmentMode"),
    })

if __name__ == "__main__":
    main()
