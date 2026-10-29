r"""Fix the PASDA TLS chain error without disabling certificate verification.

Run:  python tools\fix_pasda_tls.py

Steps:
  1. Read the server certificate from mapservices.pasda.psu.edu (no data is read).
  2. Follow the certificate's published "caIssuers" links up the chain, saving each
     NON-self-signed certificate (intermediates / cross-certificates) to data\certs\.
     A self-signed root fetched over plain HTTP is never saved: trusting it would be
     trusting whatever the network handed us. The chain must end at a root your system
     already trusts.
  3. Re-test with system roots + saved certificates.
  4. If that still fails, test PASDA's alternate hostnames (maps., services.) which may
     send a complete chain; the app can be pointed at whichever verifies.
"""
import json
import pathlib
import socket
import ssl
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "data" / "certs"
HOST = "mapservices.pasda.psu.edu"
ALTERNATES = [
    ("maps.pasda.psu.edu", "https://maps.pasda.psu.edu/ArcGIS/rest/services/pasda/AlleghenyCounty/MapServer?f=json"),
    ("services.pasda.psu.edu", "https://services.pasda.psu.edu/arcgis/rest/services/pasda/AlleghenyCounty/MapServer?f=json"),
]
TEST = (f"https://{HOST}/server/rest/services/pasda/AlleghenyCounty/MapServer/37/query"
        "?where=1%3D1&returnCountOnly=true&f=json")
UA = {"User-Agent": "HomeKeeper-prototype tls-fix"}


def decode_der(der: bytes) -> dict:
    pem = ssl.DER_cert_to_PEM_cert(der)
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(pem); path = f.name
    try:
        return ssl._ssl._test_decode_cert(path)
    finally:
        pathlib.Path(path).unlink(missing_ok=True)


def names(cert, key):
    return dict(x[0] for x in cert.get(key, ()))


def server_cert(host):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, 443), timeout=15) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as s:
            return s.getpeercert(binary_form=True)


def fetch_cert(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        data = r.read()
    pem = data.decode("ascii") if data.startswith(b"-----BEGIN") else ssl.DER_cert_to_PEM_cert(data)
    return pem, decode_der(ssl.PEM_cert_to_DER_cert(pem))


def context_with_saved():
    ctx = ssl.create_default_context()
    for p in sorted(CERT_DIR.glob("*.pem")) if CERT_DIR.exists() else []:
        ctx.load_verify_locations(cafile=str(p))
    return ctx


def try_url(url, ctx):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25, context=ctx) as r:
        return r.getcode(), r.read()[:120]


def main():
    print(f"--- 1. server certificate from {HOST} ---")
    cert = decode_der(server_cert(HOST))
    print("subject:", names(cert, "subject").get("commonName"), "| issuer:", names(cert, "issuer").get("commonName"))

    print("\n--- 2. follow caIssuers links (saving intermediates only) ---")
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    cur, hop, saved = cert, 0, []
    while hop < 5:
        urls = list(cur.get("caIssuers", ()))
        if not urls:
            print("chain stops: no caIssuers link on", names(cur, "subject").get("commonName")); break
        try:
            pem, nxt = fetch_cert(urls[0])
        except (ssl.SSLError, ValueError) as e:
            print(f"hop {hop+1}: {urls[0]} is not a single X.509 certificate (likely a PKCS#7 bundle) — stopping here.")
            print("          This is normally the root. Let Windows install it via its trusted root program:")
            print("          certutil -urlfetch -verify data\\certs\\pasda_chain_1.pem")
            break
        subj, iss = names(nxt, "subject"), names(nxt, "issuer")
        self_signed = subj == iss
        print(f"hop {hop+1}: {subj.get('commonName')}  <- issued by {iss.get('commonName')}  "
              f"[{'SELF-SIGNED ROOT, not saved' if self_signed else 'intermediate/cross-cert, saved'}]  expires {nxt.get('notAfter')}")
        if self_signed:
            break
        out = CERT_DIR / f"pasda_chain_{hop+1}.pem"
        out.write_text(pem, encoding="ascii"); saved.append(out)
        cur, hop = nxt, hop + 1

    print("\n--- 3. re-test with system roots + saved certificates ---")
    try:
        code, body = try_url(TEST, context_with_saved())
        print("HTTP", code, body.decode("utf-8", "replace"))
        print("\nFixed. The app loads data\\certs\\*.pem automatically. Run: python homekeeper.py doctor")
        return 0
    except Exception as e:
        print("still failing:", e)

    print("\n--- 4. alternate PASDA hostnames ---")
    ok = []
    for host, url in ALTERNATES:
        try:
            code, body = try_url(url, ssl.create_default_context())
            print(f"{host}: HTTP {code} with default trust store  -> usable")
            ok.append(host)
        except Exception as e:
            print(f"{host}: {e}")
    if ok:
        print(f"\nSend this output back; I will point the app at {ok[0]}.")
    else:
        print("\nSend this output back.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
