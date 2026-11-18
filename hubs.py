# hubs.py
from box_sdk_gen import (
    BoxAPIError,
    BoxClient,
    CreateCollaborationAccessibleBy,
    CreateCollaborationAccessibleByTypeField,
    CreateCollaborationItem,
    CreateCollaborationItemTypeField,
    CreateCollaborationRole,
    CreateHubCollaborationV2025R0AccessibleBy,
    CreateHubCollaborationV2025R0Hub,
    FolderReferenceV2025R0,
    HubItemOperationV2025R0,
    HubItemOperationV2025R0ActionField,
)

ALREADY_COLLABORATOR_CODES = {"user_already_collaborator", "conflict"}

def list_hub_items(client: BoxClient, hub_id: str) -> list:
    items, marker = [], None
    while True:
        page = client.hub_items.get_hub_items_v2025_r0(hub_id, marker=marker)
        items.extend(page.entries or [])
        marker = page.next_marker
        if not marker:
            return items

def get_or_create_hub(client: BoxClient, hub_id: str | None, title: str, description: str) -> str:
    if hub_id:
        hub = client.hubs.get_hub_by_id_v2025_r0(hub_id)
        print(f"Using existing hub: {hub.title} (ID: {hub.id})")
    else:
        hub = client.hubs.create_hub_v2025_r0(title, description=description)
        print(f"Created hub: {hub.title} (ID: {hub.id})")
    client.hubs.update_hub_by_id_v2025_r0(hub.id, is_ai_enabled=True)
    return hub.id

def add_folders_to_hub(client: BoxClient, hub_id: str, folder_ids: list[str]) -> None:
    existing = {item.id for item in list_hub_items(client, hub_id)}
    missing = [folder_id for folder_id in folder_ids if folder_id not in existing]
    if not missing:
        print(f"Hub {hub_id} already contains folders {', '.join(folder_ids)}")
        return
    result = client.hub_items.manage_hub_items_v2025_r0(
        hub_id,
        operations=[
            HubItemOperationV2025R0(
                action=HubItemOperationV2025R0ActionField.ADD,
                item=FolderReferenceV2025R0(id=folder_id),
            )
            for folder_id in missing
        ],
    )
    for operation in result.operations:
        print(f"Add folder {operation.item.id} to hub {hub_id}: status {operation.status} {operation.error or ''}".rstrip())

def _ignore_existing(error: BoxAPIError, message: str) -> None:
    if error.response_info.code not in ALREADY_COLLABORATOR_CODES:
        raise error
    print(message)

def add_hub_collaborator(
    client: BoxClient,
    hub_id: str,
    accessible_by: CreateHubCollaborationV2025R0AccessibleBy,
    role: str,
    label: str,
) -> None:
    try:
        client.hub_collaborations.create_hub_collaboration_v2025_r0(
            CreateHubCollaborationV2025R0Hub(id=hub_id),
            accessible_by,
            role,
        )
        print(f"Added {label} to hub {hub_id} as {role}")
    except BoxAPIError as error:
        _ignore_existing(error, f"{label} already has access to hub {hub_id}")

def share_folder_with_group(client: BoxClient, folder_id: str, group_id: str) -> None:
    try:
        client.user_collaborations.create_collaboration(
            CreateCollaborationItem(type=CreateCollaborationItemTypeField.FOLDER, id=folder_id),
            CreateCollaborationAccessibleBy(type=CreateCollaborationAccessibleByTypeField.GROUP, id=group_id),
            CreateCollaborationRole.VIEWER,
        )
        print(f"Added group {group_id} to folder {folder_id} as viewer")
    except BoxAPIError as error:
        _ignore_existing(error, f"Group {group_id} already has access to folder {folder_id}")

def configure_hub(
    client: BoxClient,
    hub_id: str,
    folder_ids: list[str],
    group_id: str,
    admin_login: str,
) -> None:
    add_folders_to_hub(client, hub_id, folder_ids)
    add_hub_collaborator(
        client,
        hub_id,
        CreateHubCollaborationV2025R0AccessibleBy(type="group", id=group_id),
        "viewer",
        f"group {group_id}",
    )
    add_hub_collaborator(
        client,
        hub_id,
        CreateHubCollaborationV2025R0AccessibleBy(type="user", login=admin_login),
        "co-owner",
        admin_login,
    )
    for folder_id in folder_ids:
        share_folder_with_group(client, folder_id, group_id)
