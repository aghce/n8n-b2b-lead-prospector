# AI B2B Lead Prospector (n8n)

An n8n workflow that researches companies for a chosen industry and region, checks that their websites are real and
fit the industry, extracts contact data from the Impressum/contact pages, drafts two outreach e-mails with an LLM,
lets a human review and edit everything in a form, stores the result in Supabase/PostgreSQL and (optionally) sends
the e-mail via SMTP.

> **Status: prototype / portfolio project.** Run it in **Test mode** only until you have read the
> [legal note](#legal-note-read-this-before-sending-anything).

## What it does

```
Form (industry, country, count)  ->  Form (region)
  -> web search for candidate companies (Groq + browser_search)
  -> drop domains already in Supabase or rejected earlier          (one small SQL query per run)
  -> scrape homepage, check it is a real company site, AI industry check
  -> pick the first N verified companies
  -> per company: scrape Impressum/contact pages -> LLM extracts data + drafts versions A/B
  -> (Telegram message with the review link)  ->  review form (edit, choose A or B, add extra text)
  -> save to Supabase  ->  optional send via SMTP  (Test mode: always to the test address)
```

Features: duplicate protection (leads + rejected sites), no personal names in the drafts (generic salutation),
e-mails in the official language of the selected country, German UI, safe test mode (all e-mails go to one test address).

## Requirements

| What | Needed for | Notes |
|---|---|---|
| n8n >= 2.x (self-hosted) | everything | tested on 2.102 |
| Supabase project (or any PostgreSQL) | storage, duplicate check | run `sql/schema.sql` once |
| Groq API key | candidate search + industry check | models `openai/gpt-oss-120b` (search) and `openai/gpt-oss-20b` (check). The free tier has a daily token limit; when it is hit the industry check is skipped with a warning |
| Google Gemini API key (or swap the model node) | drafting (Agent 1) | any n8n chat model node can replace `Gemini Model (Extractor)1` |
| Jina AI key (optional) | page scraping through `r.jina.ai` | works without a key at low rate limits |
| SMTP account | sending e-mails | only used when the action "Freigeben & E-Mail senden" is chosen |
| Telegram bot (optional) | review link as a message | leave `telegram_chat_id` empty to skip (the step then fails silently) |
| Ollama / OpenRouter (optional) | parked fallback search nodes | disabled by default, see "Optional parts" |

## Setup

1. **Database:** open the Supabase SQL editor and run [`sql/schema.sql`](sql/schema.sql).
2. **Import:** n8n -> *Workflows -> Import from file* -> `workflow/lead-prospector.workflow.json`.
3. **Credentials:** open each node with a red credential warning and select/create your own:
   Postgres (Supabase connection string, use the *session pooler* or direct connection), Groq, Google Gemini,
   Jina AI, SMTP, Telegram (optional).
4. **Config node:** open `Workflow Config` and set
   - `test_mode` - keep `true` while testing
   - `test_recipient` - the address that receives all e-mails in Test mode
   - `sender_company` - your company name for the signature
   - `email_impressum` - your legal footer / Impressum line (appended below the signature)
   - `email_extra_text` - optional text added to every e-mail
   - `telegram_chat_id` - numeric chat id (optional)
   - the `fromEmail` of the `Send Email (SMTP)` node
5. **Run:** click *Execute workflow*, open the form URL, choose industry, country, number of companies,
   then the region. When a lead is ready, open the review form (the link is also sent to Telegram).

### Test mode

`Workflow Config` has the switch `test_mode` (default `true`). While it is on, every e-mail goes only to
`test_recipient`, the subject gets a `[TEST]` prefix and the body names the real recipient. Set `test_mode` to
`false` only after the legal check below; e-mails then go to the address in the review form, and only if you pick
"Freigeben & E-Mail senden", the address is valid and the lead was not sent before.

### Review form

All fields are pre-filled. Choose *Version A* or *B*, edit subject/body, add an extra text, then choose
*Nur in Supabase speichern*, *Freigeben & E-Mail senden* or *Überspringen / Abbrechen* (skipped sites are remembered
and not suggested again for the same industry). Salutation, signature, opt-out sentence and Impressum line are added
automatically in the language of the selected country (DE, AT, CH, NL, FR, IT, ES, UK, US, CN).

## Optional parts

* **Ollama / OpenRouter search:** the nodes `Agent 0a: Ollama`, `Parse Ollama Result`,
  `Agent 0c: OpenRouter :online` and `Parse Search Result` are disabled. To use Ollama instead of Groq, enable
  `Agent 0a` + `Parse Ollama Result` and connect `Ensure Tables` -> `Build Search Prompt` -> `Agent 0a`.
* **Run from Telegram:** not implemented (needs a public HTTPS URL for a Telegram Trigger, or polling via `getUpdates`).

## Publishing your own copy safely

Never commit a raw n8n export. It contains credential ids, e-mail addresses and possibly lead data.

```bash
python scripts/sanitize_workflow.py my-export.json workflow/lead-prospector.workflow.json --company "Example GmbH"
```

The script replaces credentials, e-mail addresses and company names, clears chat/webhook ids and sets
`active=false`. Read the result once before pushing. Also never commit database exports of real leads.

## Legal note (read this before sending anything)

This is general information, not legal advice. Cold e-mail advertising in Germany is restricted:

* **UWG section 7 (2) no. 2:** advertising e-mail generally needs the recipient's prior explicit consent - also
  towards companies. "Presumed consent" is accepted for B2B *phone* calls, not for e-mail. An opt-out sentence does
  not replace consent.
* **GDPR:** storing names and business e-mail addresses of natural persons needs a legal basis (usually
  legitimate interest, Art. 6(1)(f)) and an information notice (Art. 14), including the data source.
* Include a proper sender identification/Impressum and an easy opt-out, and honour opt-outs immediately.
* Scraping may conflict with a site's terms of use.

Safe ways to use this project: research and drafting with human review, outreach through channels that are
allowed (phone with presumed consent, letters, contact forms, LinkedIn within its rules), or e-mails to people who
opted in. Keep Test mode on while developing and talk to a lawyer before any real campaign.

## Known limitations

* The web search can return fewer companies than requested; the workflow then continues with what it found.
* Groq free-tier daily token limits can pause the industry check (it then passes with a warning note).
* Jina can fail on JavaScript-heavy sites; e-mail addresses shown as images are not readable.
* The review form can show a blank page if opened before the run is waiting; reload it or use the Telegram link.

## Repository layout

```
workflow/lead-prospector.workflow.json   sanitized n8n workflow (import this)
sql/schema.sql                           tables, indexes, RLS
scripts/sanitize_workflow.py             removes secrets/personal data from an export
```
