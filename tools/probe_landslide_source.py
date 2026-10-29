r"""Diagnostic for the one failed doctor check (PASDA landslide layer: TLS chain error on Windows).

Run:  python tools\probe_landslide_source.py
It (1) prints the certificate chain PASDA presents, so the missing intermediate CA can be identified,
and (2) lists Allegheny County's own ArcGIS "OPENDATA" services to see whether the county hosts the
landslide layer itself (which would avoid PASDA entirely). It reads public metadata only.
"""
import json
import socket
import ssl
import sys
import urllib.request

HOST = "mapservices.pasda.psu.edu"
COUNTY = "https://gisdata.alleghenycounty.us/arcgis/rest/services/OPENDATA?f=json"

print(f"--- TLS chain presented by {HOST} (verification disabled for this diagnostic only; no data is read) ---")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    with socket.create_connection((HOST, 443), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=HOST) as s:
            cert = s.getpeercert(binary_form=False)
            if cert:
                print("subject:", dict(x[0] for x in cert.get("subject", ())))
                print("issuer: ", dict(x[0] for x in cert.get("issuer", ())))
                print("notAfter:", cert.get("notAfter"))
            else:
                # CERT_NONE returns no parsed dict on some builds; fall back to raw DER length
                der = s.getpeercert(binary_form=True)
                print("peer cert bytes:", len(der) if der else None, "(parsed dict unavailable with CERT_NONE)")
            try:
                chain = s.get_verified_chain() if hasattr(s, "get_verified_chain") else None
            except Exception:
                chain = None
            print("chain objects available:", bool(chain))
except Exception as e:
    print("TLS probe failed:", e)

print(f"\n--- Allegheny County ArcGIS OPENDATA services ---")
try:
    req = urllib.request.Request(COUNTY, headers={"User-Agent": "HomeKeeper-prototype probe"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    names = [s.get("name") for s in d.get("services", [])]
    print(f"{len(names)} services")
    for n in names:
        flag = "  <-- candidate" if any(k in n.lower() for k in ("slide", "slope", "hazard", "geolog")) else ""
        print(" ", n, flag)
except Exception as e:
    print("county probe failed:", e)

print("\nDone. Send this output back.")
