"""Configura los entregables Postman con la URL pública real, sin realizar peticiones."""
import argparse
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL HTTPS de la API desplegada, sin /books ni /docs")
    args = parser.parse_args()
    url = args.url.rstrip("/")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        parser.error("Usa una URL base HTTPS pública, sin ruta, credenciales ni parámetros.")
    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith((".local", ".localhost", ".example", ".invalid")):
        parser.error("Usa el dominio público real del despliegue.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            parser.error("La IP debe ser pública.")
    root = Path(__file__).resolve().parents[1] / "postman"
    environment_file = root / "production.postman_environment.json"
    environment = json.loads(environment_file.read_text(encoding="utf-8"))
    environment["values"][0]["value"] = url
    collection_file = root / "bookstore.postman_collection.json"
    collection = json.loads(collection_file.read_text(encoding="utf-8"))
    for variable in collection["variable"]:
        if variable["key"] == "base_url":
            variable["value"] = url
    for file, value in [(environment_file, environment), (collection_file, collection)]:
        file.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Colección y entorno Producción configurados para {url}")
    print("Ejecuta la colección contra esta URL para verificar el despliegue.")


if __name__ == "__main__":
    main()
