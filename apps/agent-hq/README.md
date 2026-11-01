# Palm92 Agent HQ

A local-first, human-governed workspace for routing requests to specialists, keeping shared project context, and reviewing AI drafts.

**AI investigates. Humans decide.**

## What works

- Mobile-friendly dashboard with a request queue, notes, notifications, approvals, WhatsApp inbox, and specialist directory.
- Explainable keyword routing to seven specialist roles.
- Optional two-step AI workflow: the selected specialist prepares a draft, then the Chief of Staff reviewer checks it. The user sees both outputs and must review them.
- Lesson-to-outcome companion: turn a user-supplied lesson or idea into a project-specific implementation brief or reusable skill draft, with a second-agent review.
- Verified WhatsApp Cloud API webhook; incoming text is deduplicated, stored, and queued for a specialist.
- Outbound WhatsApp text replies require a human approval, an allowlisted opted-in recipient, and a recent incoming message. Approval and sending are separate actions.
- Hosted sign-in gate with signed, expiring session cookies. Vercel and Replit deployments require authentication secrets before serving the dashboard.
- Reusable workflow skill in `SKILL.md`.

## Important limits

This is a usable local application and an integration-ready build, not a live WhatsApp service yet. No WhatsApp account, business number, API token, OpenAI API key, or public Agent HQ deployment is connected. The agent runtime is off until configured. AI API usage can be billed to the configured API account.

The data store is SQLite on the local filesystem and is not encrypted by this app. Keep it on a private device. Do not host personal or customer data publicly until a durable, protected database, retention/deletion policy, access review, and HTTPS deployment are configured. The existing Palm92 Vercel project serves the repository root app, not this sub-app.

The agents cannot run shell commands, publish content, spend money, change accounts, or send a message without a separate human approval action.

## Run privately on your computer

Python 3.11 or newer is recommended.

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
~~~

Open http://127.0.0.1:3870. The default bind is loopback, so the app is only reachable from the same computer. SQLite is created under `data/agent-hq.sqlite3`.

## Enable the AI specialist and reviewer

1. Create or use an OpenAI API account and set `OPENAI_API_KEY` and `OPENAI_MODEL` in the private server environment. ChatGPT subscriptions and API billing are separate.
2. Restart the app and confirm the dashboard shows **TEAM RUNTIME · READY**.
3. Use **Run agent team** on a queued request. The app asks for confirmation before sending that request and the latest shared notes to the OpenAI API. That request makes two model calls and may incur usage charges.
4. Review the specialist draft and Chief of Staff review. The app does not perform any external action from those drafts.

Never place an API key in a browser form, shared note, GitHub commit, or chat.

## Turn learning into a project result

Open **Lesson to outcome**, choose a lesson title and one of your projects, then paste notes or an excerpt you have the right to use. Start **Create reviewed draft** only when you are ready to send that text to the configured OpenAI API. The specialist creates a brief or skill draft; the Chief of Staff checks it. Agent HQ saves the generated result and review, not the submitted source transcript. Personal memory notes are not sent as model context. Review assumptions and verify facts before you use the draft or install a skill.

## Connect WhatsApp

Live use requires a Meta business portfolio, WhatsApp Business Account, a registered business phone number, access token, phone-number ID, app secret, verify token, and a public HTTPS callback. Meta's hosted Cloud API documentation lists the required business assets and token setup: https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api

Set these values in the private server environment, never in source control:

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_API_VERSION`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_ALLOWED_RECIPIENTS`

Then configure `https://YOUR-HOST/webhook` in Meta, verify with the same webhook token, and subscribe to the `messages` webhook field. The app validates `X-Hub-Signature-256` and deduplicates message IDs. Inbound text becomes a queued task. Outgoing messages remain disabled unless the recipient has opted in, is allowlisted, has messaged within the 24-hour reply window, and the draft is approved.

Use a Meta test number first. Do not move a personal number to the Cloud API without checking Meta's current number migration and app coexistence rules.

## Hosted deployment gate

The app refuses public binding without `AGENT_HQ_ADMIN_PASSWORD` (at least 14 characters) and `AGENT_HQ_SESSION_SECRET` (at least 32 random characters). Generate a secret locally with:

~~~bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
~~~

The current app uses local SQLite, so a Vercel preview status does not mean this sub-app is deployed or has durable storage. Before exposing it to the internet, move to a private host with a persistent, protected database, add retention/deletion controls, configure HTTPS and secrets, then verify authenticated access and WhatsApp webhook delivery. Do not put the Meta webhook behind login; it is separately protected by Meta signature verification.

## Skill and project files

- `app.py`: Starlette application, auth/session checks, SQLite store, optional OpenAI Responses API workflow, WhatsApp Cloud API adapter.
- `SKILL.md`: repeatable Palm92 Agent HQ build and guided immersion workflow.
- `.env.example`: configuration names only; all secrets are blank.
- `requirements.txt`: Python dependencies.
