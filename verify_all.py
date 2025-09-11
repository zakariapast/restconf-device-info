import json
import requests
from requests.auth import HTTPBasicAuth

HOST = "https://sandbox-iosxe-latest-1.cisco.com:443"
USER = "developer"
PWD  = "C1sco12345"

def get(path):
    url = f"{HOST}/restconf/data/{path}"
    r = requests.get(url, auth=HTTPBasicAuth(USER, PWD),
                     headers={"Accept": "application/yang-data+json"},
                     verify=False, timeout=15)
    return r.status_code, (r.json() if r.content else {})

checks = {
    "hostname": "Cisco-IOS-XE-native:native/hostname",
    "domain_name": "Cisco-IOS-XE-native:native/ip/domain/name",
    "banner_motd": "Cisco-IOS-XE-native:native/banner/motd/banner",
    "ntp": "Cisco-IOS-XE-native:native/ntp",
    "loopback100": "ietf-interfaces:interfaces/interface=Loopback100",
}

out = {}
for label, path in checks.items():
    code, body = get(path)
    out[label] = {"http": code, "body": body}

print(json.dumps(out, indent=2))
