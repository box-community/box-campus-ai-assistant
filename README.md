# Box campus AI assistant

A minimal, runnable reference for a campus AI assistant built on Box Hubs. A
provisioning script creates one Box Hub per student service, such as
Admissions and Housing, plus a campus-wide hub that combines every service
folder. A small Flask portal then embeds
[Box Hubs AI Chat](https://developer.box.com/guides/embed/box-embed) so
students can ask questions and get answers from approved documents only.

The chat runs with each student's own Box session, so it never answers from
content the student cannot open in Box. Access is managed through one Box
group: add or remove a student from the group, and nothing else changes.

The companion repository to the tutorial is:
**[Build a campus AI assistant portal with Box Hubs AI Chat](https://developer.box.com/tutorials/campus-ai-assistant)**.

## What it does

| Capability | How |
| --- | --- |
| Create or reuse one hub per service and a campus-wide hub | `POST /2.0/hubs` or `GET /2.0/hubs/:id`, with hub IDs saved to `portal-config.json` |
| Turn on Box AI for each hub | `PUT /2.0/hubs/:id` with `is_ai_enabled: true` |
| Add the service folders to the hubs | `GET /2.0/hub_items` and `POST /2.0/hubs/:id/manage_items`, adding only missing folders |
| Give students and the hub admin access | `POST /2.0/hub_collaborations` (group as viewer, admin as co-owner) and `POST /2.0/collaborations` (group as viewer on each folder) |
| Ask the whole campus | The home page embeds the Box AI chat button for the campus-wide hub |
| Ask one service | Each service page embeds the hub's AI chat widget and lists its sources |

All Hubs API calls use API version 2025.0 through the SDK's `*_v2025_r0`
methods.

## Project layout

```text
box-campus-ai-assistant/
├── box_client.py               # CCG service account auth
├── seed.py                     # Creates sample folders, documents, and the students group
├── sample-docs/                # Fictional Admissions and Housing documents for seed.py
├── hubs.py                     # Create or reuse hubs, add folders and collaborators
├── provision_hubs.py           # Provisions every hub from hubs.config.json
├── portal.py                   # Flask portal that embeds Hubs AI Chat
├── hubs.config.json            # Services and their Box folder IDs
├── portal-config.json.example  # Shape of the file provision_hubs.py writes (used by CI only)
├── templates/
│   ├── home.html
│   └── service.html
├── requirements.txt
├── .env.example
└── .gitignore
```

## Prerequisites

- **Python 3.11+**
- A [free Box developer account](https://account.box.com/signup/developer),
  or a [Box Enterprise account](https://www.box.com/pricing) with **Box Hubs**
  and **Box AI for Hubs** enabled. See
  [Configuring Box Hubs](https://support.box.com/hc/en-us/articles/25822332454547-Configuring-Box-Hubs).
- A **Client Credentials Grant (CCG)** Platform App, **authorized** in the
  Admin Console, with these scopes enabled:
  - **Read and write all files and folders stored in Box**
  - **Manage groups**, so that the scripts can create the students group and
    invite it to the service folders
  - **Manage users**, so that `seed.py` can find your test student by email
- The app's **App Access Level** set to **App + Enterprise Access** on the
  **Configuration** tab. With the default **App Access Only**, the app cannot
  see the users in your enterprise, so `seed.py` cannot find your test student.
  After you change the access level, an admin must re-authorize the app in the
  Admin Console.
- Every student who uses the portal needs a Box account in your enterprise and
  must be signed in to Box in the same browser.

## Setup

1. **Clone and enter the project**

   ```bash
   git clone https://github.com/box-community/box-campus-ai-assistant.git
   cd box-campus-ai-assistant
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

3. **Configure credentials**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in:

   - `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, and `BOX_ENTERPRISE_ID`
   - `HUB_ADMIN_LOGIN`: the Box user who maintains student-facing content.
     The scripts give them access to the folders and make them a co-owner of
     every hub, so they can manage both in the Box web app.
   - `TEST_STUDENT_LOGIN`: a Box user in your enterprise who is not an admin.
     You sign in as this user to test the portal.

   Leave `STUDENTS_GROUP_ID` empty. If your enterprise uses a custom Box
   domain, set `BOX_EMBED_DOMAIN` to it.

   > **Never commit `.env`.** It is already in `.gitignore`.

4. **Seed the sample content**

   ```bash
   python3 seed.py
   ```

   The script runs as the app's service account. It creates the `Admissions`
   and `Housing` folders, uploads the fictional documents from `sample-docs/`,
   and invites the hub admin to the folders as an editor. It then creates the
   `Students` group and adds the test student. It writes the folder IDs to
   `hubs.config.json` and the group ID to `.env`:

   ```text
   == Admissions ==
   Created folder: Admissions (ID: 111111)
   Uploaded admission-requirements.md to folder 111111
   Uploaded application-deadlines.md to folder 111111
   Added hub.admin@example.edu to folder 111111 as editor
   ...
   == Students group ==
   Created group: Students (ID: 333333)
   Added student@example.edu to group 333333

   Wrote folder IDs to hubs.config.json and STUDENTS_GROUP_ID to .env.
   Next, run: python3 provision_hubs.py
   ```

   You can run it again safely. It reuses the folders, files, and group it
   finds by name.

### Use your own folders and group

To use your offices' existing documents instead of the sample content, skip
`seed.py` and:

1. Invite the app's service account as an **Editor** on each service folder.
   Find its email in the Developer Console > your app > **Configuration** >
   **App Details** sidebar > **Service Account ID** (it looks like
   `AutomationUser_xxxxx_xxxxxx@boxdevedition.com`). Without this
   collaboration, API calls return `404 Not Found`.
2. Add each folder ID to `hubs.config.json`, replacing
   `<ADMISSIONS_FOLDER_ID>` and `<HOUSING_FOLDER_ID>`.
3. Set `STUDENTS_GROUP_ID` in `.env` to the ID of an existing group of
   students.

## Run

1. **Provision the hubs**

   ```bash
   python3 provision_hubs.py
   ```

   You should see each hub confirmed, followed by the path of the portal
   configuration:

   ```text
   == Admissions ==
   Created hub: Admissions (ID: 1000001)
   Add folder 111111 to hub 1000001: status 200
   Added group 333333 to hub 1000001 as viewer
   Added hub.admin@example.edu to hub 1000001 as co-owner
   Added group 333333 to folder 111111 as viewer
   ...
   Wrote portal-config.json with 3 hubs.
   ```

   Run the script again. It reuses the hubs from `portal-config.json` and
   reports that the folders and collaborators already exist, instead of
   creating new hubs.

   > Keep `portal-config.json`. If you delete it, the next run creates a new
   > set of hubs. It is in `.gitignore` because it holds your hub IDs.

2. **Check the hubs in Box.** Sign in as the hub admin, select **Hubs** in the
   left sidebar, and open **Admissions**, **Housing**, and **Campus
   Assistant**. Allow a few minutes for Box to index the files before you test
   the chat.

3. **Update the chat button script.** In the **Campus Assistant** hub, open the
   menu in the upper-right corner and select **Embed**. On the **Hub AI Chat**
   tab, select **Chat button**, and copy the `src` value of the `script` tag
   into `BOX_CHAT_BUTTON_SCRIPT` in `.env`.

4. **Start the portal**

   ```bash
   python3 portal.py
   ```

   The portal starts on `http://localhost:3000` (with auto-reload enabled).

   > Do not use `debug=True` in production.

## Try it

In a browser where you are signed in to Box as the test student, open
`http://localhost:3000`.

- On the home page, select **Ask the campus** and ask a question that one of
  your documents answers, such as "When is the move-in date?". Confirm that
  the answer cites the document.
- Select **Admissions**. The page lists the Admissions folder under
  **Sources**, and the chat answers admissions questions.
- Select the close button in the chat. The chat hides and **Open chat**
  displays. Select **Open chat** to display the chat again.

### Add a student service

Add an entry to `hubs.config.json`. To seed it, add its documents to
`sample-docs/<slug>/` and run `python3 seed.py`, which creates a folder named
after the service's `title`. Otherwise, share your own folder with the service
account and set its `folderId`. Then run `python3 provision_hubs.py`. The
script creates the new hub, adds the new folder to the campus-wide hub, and
updates `portal-config.json`. Restart the portal to display the new service.

## How it works

1. `seed.py` creates the service folders and the students group as the
   service account, so the service account owns them and needs no extra
   collaboration.
2. `provision_hubs.py` reads `hubs.config.json` and, for each service, gets or
   creates a hub, turns on Box AI, and saves the hub ID to
   `portal-config.json` right away. A run that fails partway reuses the same
   hubs next time.
3. `hubs.py` adds only the folders that are not in the hub yet, adds the
   students group as a viewer and the hub admin as a co-owner, and adds the
   group as a viewer on each folder. Hub access does not grant file access, so
   the folder collaboration is required. Existing access is reported, not
   treated as an error.
4. `portal.py` fills the page templates with the hub IDs and lists each hub's
   sources, cached for 5 minutes.
5. The chat button and the chat widget run with the student's own Box
   session. Neither uses a shared link, so only hub collaborators can use the
   chat.

## Security notes

- Keep the client secret and enterprise ID server-side.
- Box AI answers only from the files in the service folders. Keep drafts and
  outdated versions out of them.
- Manage access through the students group instead of individual
  collaborations.
- Before you deploy, run the portal on a production server instead of the
  Flask development server, and serve it over HTTPS.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate`. |
| `invalid_client` | Check `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, and `BOX_ENTERPRISE_ID` in `.env`, and make sure the app is authorized in the Admin Console. |
| `404 Not Found` | If you use your own folders, invite the service account as **Editor** on every folder in `hubs.config.json`. |
| `seed.py` reports `No user with login ... found` | Check `TEST_STUDENT_LOGIN` in `.env`. Then, on the **Configuration** tab in the Developer Console, make sure **Manage users** is enabled and the **App Access Level** is **App + Enterprise Access**, save, and re-authorize the app. Without either setting, Box returns no users instead of an error. Run `seed.py` again; it reuses what it already created. |
| `403 insufficient_scope` when creating the group or adding it to a folder | Enable **Manage groups** in the Developer Console, save, and re-authorize the app. Then run the script again; it reuses what it already created. |
| `No such file or directory: 'portal-config.json'` | Run `python3 provision_hubs.py` first, and start the portal from the project directory. |
| `localhost:5000` returns 403 on macOS | AirPlay Receiver uses port 5000. Keep `PORT=3000` in `.env`. |
| The chat returns empty or generic answers | Wait a few minutes for indexing, confirm the student is in the students group, and make sure your documents contain text (scanned PDFs without OCR are not searchable). |

## License

[MIT](./LICENSE)
