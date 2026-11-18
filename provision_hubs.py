# provision_hubs.py
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from box_client import get_box_client
from hubs import configure_hub, get_or_create_hub

load_dotenv()

HUBS_CONFIG = Path("hubs.config.json")
PORTAL_CONFIG = Path("portal-config.json")

def save_portal_config(config: dict, hub_ids: dict[str, str], campus_hub_id: str | None) -> None:
    services = [
        {
            "slug": service["slug"],
            "title": service["title"],
            "description": service["description"],
            "hubId": hub_ids[service["slug"]],
        }
        for service in config["services"]
        if service["slug"] in hub_ids
    ]
    PORTAL_CONFIG.write_text(json.dumps({"campusHubId": campus_hub_id, "services": services}, indent=2) + "\n")

def main() -> None:
    config = json.loads(HUBS_CONFIG.read_text())
    previous = json.loads(PORTAL_CONFIG.read_text()) if PORTAL_CONFIG.exists() else {}
    hub_ids = {service["slug"]: service["hubId"] for service in previous.get("services", [])}
    campus_hub_id = previous.get("campusHubId")
    group_id = os.getenv("STUDENTS_GROUP_ID")
    admin_login = os.getenv("HUB_ADMIN_LOGIN")

    client = get_box_client()

    for service in config["services"]:
        print(f"\n== {service['title']} ==")
        hub_id = get_or_create_hub(client, hub_ids.get(service["slug"]), service["title"], service["description"])
        hub_ids[service["slug"]] = hub_id
        save_portal_config(config, hub_ids, campus_hub_id)
        configure_hub(client, hub_id, [service["folderId"]], group_id, admin_login)

    campus = config["campusHub"]
    print(f"\n== {campus['title']} ==")
    campus_hub_id = get_or_create_hub(client, campus_hub_id, campus["title"], campus["description"])
    save_portal_config(config, hub_ids, campus_hub_id)
    configure_hub(
        client,
        campus_hub_id,
        [service["folderId"] for service in config["services"]],
        group_id,
        admin_login,
    )

    print(f"\nWrote {PORTAL_CONFIG} with {len(config['services']) + 1} hubs.")

if __name__ == "__main__":
    main()
