import os, csv, time
from pathlib import Path
from dotenv import load_dotenv
import meraki

load_dotenv()
API_KEY = os.getenv("MERAKI_API_KEY")
if not API_KEY:
    raise SystemExit("Set MERAKI_API_KEY in .env")

# single Dashboard session (built-in retry & rate-limit handling)
dashboard = meraki.DashboardAPI(API_KEY, suppress_logging=True, maximum_retries=5)

def main():
    Path("output").mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    # 1) orgs
    orgs = dashboard.organizations.getOrganizations()
    org_rows = [{"orgId": o["id"], "name": o["name"]} for o in orgs]
    with open(f"output/meraki_orgs_{ts}.csv", "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=["orgId","name"]).writerows([{"orgId":"orgId","name":"name"}, *org_rows])

    # (choose the first org by default; you can change later)
    org_id = orgs[0]["id"]

    # 2) networks
    nets = dashboard.organizations.getOrganizationNetworks(org_id)
    net_rows = [{"orgId":org_id, "netId":n["id"], "name":n["name"], "productTypes":",".join(n.get("productTypes",[]))} for n in nets]
    with open(f"output/meraki_networks_{ts}.csv","w",newline="",encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=["orgId","netId","name","productTypes"]).writerows(
            [{"orgId":"orgId","netId":"netId","name":"name","productTypes":"productTypes"}, *net_rows]
        )

    # 3) devices per network
    dev_fields = ["orgId","netId","serial","model","name","mac","lanIp","publicIp"]
    with open(f"output/meraki_devices_{ts}.csv","w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=dev_fields); w.writeheader()
        for n in nets:
            devices = dashboard.networks.getNetworkDevices(n["id"])
            for d in devices:
                w.writerow({
                    "orgId": org_id, "netId": n["id"], "serial": d.get("serial"),
                    "model": d.get("model"), "name": d.get("name"),
                    "mac": d.get("mac"), "lanIp": d.get("lanIp"), "publicIp": d.get("publicIp")
                })
    print("[OK] Wrote orgs/networks/devices CSVs in output/")

if __name__ == "__main__":
    main()
