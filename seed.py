# seed.py
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key
from box_sdk_gen import (
    BoxAPIError,
    BoxClient,
    CreateCollaborationAccessibleBy,
    CreateCollaborationAccessibleByTypeField,
    CreateCollaborationItem,
    CreateCollaborationItemTypeField,
    CreateCollaborationRole,
    CreateFolderParent,
    CreateGroupMembershipGroup,
    CreateGroupMembershipUser,
    UploadFileAttributes,
    UploadFileAttributesParentField,
)

from box_client import get_box_client
from hubs import ALREADY_COLLABORATOR_CODES

load_dotenv()

ENV_FILE = Path(".env")
HUBS_CONFIG = Path("hubs.config.json")
SAMPLE_DOCS = Path("sample-docs")
GROUP_NAME = "Students"

def list_folder_items(client: BoxClient, folder_id: str) -> list:
    items, marker = [], None
    while True:
        page = client.folders.get_folder_items(folder_id, usemarker=True, marker=marker, limit=1000)
        items.extend(page.entries or [])
        marker = page.next_marker
        if not marker:
            return items

def get_or_create_folder(client: BoxClient, name: str) -> str:
    for item in list_folder_items(client, "0"):
        if item.type.value == "folder" and item.name == name:
            print(f"Using existing folder: {name} (ID: {item.id})")
            return item.id
    folder = client.folders.create_folder(name, CreateFolderParent(id="0"))
    print(f"Created folder: {name} (ID: {folder.id})")
    return folder.id

def upload_sample_docs(client: BoxClient, folder_id: str, docs_dir: Path) -> None:
    existing = {item.name for item in list_folder_items(client, folder_id)}
    for path in sorted(docs_dir.glob("*")):
        if path.name in existing:
            print(f"File {path.name} already exists in folder {folder_id}")
            continue
        with path.open("rb") as file:
            client.uploads.upload_file(
                UploadFileAttributes(name=path.name, parent=UploadFileAttributesParentField(id=folder_id)),
                file,
            )
        print(f"Uploaded {path.name} to folder {folder_id}")

def share_folder_with_user(client: BoxClient, folder_id: str, login: str) -> None:
    try:
        client.user_collaborations.create_collaboration(
            CreateCollaborationItem(type=CreateCollaborationItemTypeField.FOLDER, id=folder_id),
            CreateCollaborationAccessibleBy(type=CreateCollaborationAccessibleByTypeField.USER, login=login),
            CreateCollaborationRole.EDITOR,
        )
        print(f"Added {login} to folder {folder_id} as editor")
    except BoxAPIError as error:
        if error.response_info.code not in ALREADY_COLLABORATOR_CODES:
            raise
        print(f"{login} already has access to folder {folder_id}")

def get_or_create_group(client: BoxClient, name: str) -> str:
    for group in client.groups.get_groups(filter_term=name).entries or []:
        if group.name == name:
            print(f"Using existing group: {name} (ID: {group.id})")
            return group.id
    group = client.groups.create_group(name)
    print(f"Created group: {name} (ID: {group.id})")
    return group.id

def find_user_id(client: BoxClient, login: str) -> str:
    for user in client.users.get_users(filter_term=login).entries or []:
        if user.login.lower() == login.lower():
            return user.id
    sys.exit(
        f"No user with login {login} found. Check TEST_STUDENT_LOGIN in .env, and make sure "
        "the app has the Manage users scope and App + Enterprise Access. Without them, Box returns no users."
    )

def add_group_member(client: BoxClient, group_id: str, login: str) -> None:
    user_id = find_user_id(client, login)
    members, offset = [], 0
    while True:
        page = client.memberships.get_group_memberships(group_id, limit=100, offset=offset)
        entries = page.entries or []
        members.extend(membership.user.id for membership in entries if membership.user)
        if len(entries) < 100:
            break
        offset += 100
    if user_id in members:
        print(f"{login} is already a member of group {group_id}")
        return
    client.memberships.create_group_membership(
        CreateGroupMembershipUser(id=user_id),
        CreateGroupMembershipGroup(id=group_id),
    )
    print(f"Added {login} to group {group_id}")

def main() -> None:
    admin_login = os.getenv("HUB_ADMIN_LOGIN")
    student_login = os.getenv("TEST_STUDENT_LOGIN")
    if not admin_login or not student_login:
        sys.exit("Set HUB_ADMIN_LOGIN and TEST_STUDENT_LOGIN in .env before you run seed.py.")

    config = json.loads(HUBS_CONFIG.read_text())
    client = get_box_client()

    for service in config["services"]:
        print(f"\n== {service['title']} ==")
        folder_id = get_or_create_folder(client, service["title"])
        service["folderId"] = folder_id
        HUBS_CONFIG.write_text(json.dumps(config, indent=2) + "\n")
        upload_sample_docs(client, folder_id, SAMPLE_DOCS / service["slug"])
        share_folder_with_user(client, folder_id, admin_login)

    print(f"\n== {GROUP_NAME} group ==")
    group_id = get_or_create_group(client, GROUP_NAME)
    set_key(ENV_FILE, "STUDENTS_GROUP_ID", group_id, quote_mode="never")
    add_group_member(client, group_id, student_login)

    print(f"\nWrote folder IDs to {HUBS_CONFIG} and STUDENTS_GROUP_ID to {ENV_FILE}.")
    print("Next, run: python3 provision_hubs.py")

if __name__ == "__main__":
    main()
