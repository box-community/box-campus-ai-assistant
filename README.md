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
  - **Manage groups**, so that the script can invite the students group to
    the service folders
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

3. **Create the service folders** in Box: `Admissions` and `Housing`. Upload
   each office's documents, such as application deadlines to `Admissions` and
   move-in dates to `Housing`. Note each folder ID from the URL
   (`https://app.box.com/folder/123456789` > `123456789`).

   **Critical:** invite the app's service account as an **Editor** on both
   folders. Find the service account email in Developer Console > your app >
   **Configuration** > **App Details** sidebar > **Service Account ID** (looks
   like `AutomationUser_xxxxx_xxxxxx@boxdevedition.com`). Without this
   collaboration, API calls return `404 Not Found`. Editor access is required
   because the script invites the students group to the folders.

4. **Create the students group** (requires Admin access). In the
   [Admin Console](https://app.box.com/master), select **Users & Groups** >
   **Groups**, create a group called `Students`, and add the students who use
   the portal. For testing, add one Box user who is not an admin. Find the
   group ID with the list groups endpoint:

   ```bash
   curl "https://api.box.com/2.0/groups?filter_term=Students" \
     -H "Authorization: Bearer <DEVELOPER_TOKEN>"
   ```

5. **Choose the hub admin**: the Box user who maintains student-facing
   content. The script adds them as a co-owner of every hub so they can manage
   the hubs in the Box web app.

6. **Configure credentials**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`,
   `BOX_ENTERPRISE_ID`, `STUDENTS_GROUP_ID`, and `HUB_ADMIN_LOGIN`. If your
   enterprise uses a custom Box domain, set `BOX_EMBED_DOMAIN` to it.

   > **Never commit `.env`.** It is already in `.gitignore`.

7. **Add your folder IDs** to `hubs.config.json`, replacing
   `<ADMISSIONS_FOLDER_ID>` and `<HOUSING_FOLDER_ID>`.

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

In a browser where you are signed in to Box as a member of the students
group, open `http://localhost:3000`.

- On the home page, select **Ask the campus** and ask a question that one of
  your documents answers, such as "When is the move-in date?". Confirm that
  the answer cites the document.
- Select **Admissions**. The page lists the Admissions folder under
  **Sources**, and the chat answers admissions questions.
- Select the close button in the chat. The chat hides and **Open chat**
  displays. Select **Open chat** to display the chat again.

### Add a student service

Create and share the service folder as in Setup, add an entry to
`hubs.config.json`, and run `python3 provision_hubs.py`. The script creates the
new hub, adds the new folder to the campus-wide hub, and updates
`portal-config.json`. Restart the portal to display the new service.

## How it works

1. `provision_hubs.py` reads `hubs.config.json` and, for each service, gets or
   creates a hub, turns on Box AI, and saves the hub ID to
   `portal-config.json` right away. A run that fails partway reuses the same
   hubs next time.
2. `hubs.py` adds only the folders that are not in the hub yet, adds the
   students group as a viewer and the hub admin as a co-owner, and adds the
   group as a viewer on each folder. Hub access does not grant file access, so
   the folder collaboration is required. Existing access is reported, not
   treated as an error.
3. `portal.py` fills the page templates with the hub IDs and lists each hub's
   sources, cached for 5 minutes.
4. The chat button and the chat widget run with the student's own Box
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
| `404 Not Found` | Invite the service account as **Editor** on every folder in `hubs.config.json`. |
| `403 insufficient_scope` when adding the group to a folder | Enable **Manage groups** in the Developer Console, save, and re-authorize the app. Then run the script again; it reuses the hubs it already created. |
| `No such file or directory: 'portal-config.json'` | Run `python3 provision_hubs.py` first, and start the portal from the project directory. |
| `localhost:5000` returns 403 on macOS | AirPlay Receiver uses port 5000. Keep `PORT=3000` in `.env`. |
| The chat returns empty or generic answers | Wait a few minutes for indexing, confirm the student is in the students group, and make sure your documents contain text (scanned PDFs without OCR are not searchable). |

## License

[MIT](./LICENSE)
