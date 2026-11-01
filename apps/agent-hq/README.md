# Palm92 Agent HQ

A local-first, human-governed agent orchestration starter based on Faith Wright's shared AI-building workflow.

**AI investigates. Humans decide.**

## Included

- A mobile-friendly Agent HQ dashboard
- A natural-language request inbox with transparent specialist routing
- Seven Palm92/Faithfulord specialist roles
- Shared knowledge, memory, and rule notes
- Notifications and auditable task/approval status
- A WhatsApp Business Cloud API webhook adapter
- Outbound WhatsApp drafts that require separate approval and send actions
- Reusable workflow skill in SKILL.md

## Current scope

This is a working local app starter. The local dispatcher uses explainable keyword rules. No LLM or coding-agent runtime is connected yet. Requests are queued for manual execution. The app does not start shell commands, create Git branches, message people automatically, or alter accounts.

The WhatsApp adapter is off until configuration is present. It receives verified webhook events and stores incoming text for human review. Outbound replies require all of the following:

1. An approved draft
2. A recipient on WHATSAPP_ALLOWED_RECIPIENTS
3. A recent incoming message from that recipient, within the 24-hour reply window
4. Meta Cloud API configuration

The adapter supports text replies only. It does not implement business-initiated message templates.

## Run locally

Python 3.11 or newer is recommended.

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
~~~

Open http://127.0.0.1:3870. The server binds to loopback by default.

The database is created at data/agent-hq.sqlite3. Keep it on a private device and back it up securely. Do not store access tokens in the database, notes, or chat.

## WhatsApp setup

Live use requires a Meta business portfolio, a WhatsApp Business Account, a registered business phone number, an access token, and a public HTTPS webhook. Configure secrets in a private environment file or secret manager, never in source control.

Set these values in .env:

- WHATSAPP_ACCESS_TOKEN
- WHATSAPP_PHONE_NUMBER_ID
- WHATSAPP_API_VERSION
- WHATSAPP_VERIFY_TOKEN
- WHATSAPP_APP_SECRET
- WHATSAPP_ALLOWED_RECIPIENTS

Use an allowlist containing only recipients who have explicitly consented to receive replies. Configure the webhook callback as https://YOUR-HOST/webhook and subscribe the app to the WhatsApp messages webhook field. Verify webhook signatures before processing events. This starter stores only incoming text message bodies and sender numbers; review retention and privacy needs before production use.

Official Meta reference: https://developers.facebook.com/docs/whatsapp/cloud-api/overview

## Safety and deployment

- Never expose the local app to the public internet without authentication and a production security review.
- Do not put medical, financial, immigration, or other sensitive records in the shared brain.
- Never add access tokens to a rule or memory note.
- Human approval is required before any WhatsApp send.
- Browser-visible approval is only a control in the local starter, not a production identity or authorization system.
- Use isolated Git branches or worktrees for concurrent coding agents. This app does not launch or stop OS processes.
- Add durable storage, authentication, encrypted secrets, retention controls, and webhook monitoring before public deployment.

## Structure

- app.py — Starlette application and local SQLite store
- SKILL.md — reusable agent-swarm build and review workflow
- .env.example — configuration names with empty secret values
