-- Schema for the AI B2B Lead Prospector (Supabase / PostgreSQL)
-- Run once in the Supabase SQL editor. The workflow also runs the
-- "CREATE TABLE IF NOT EXISTS rejected_sites" part itself (node "Ensure Tables"),
-- but the leads table must exist before the first run.

-- 1) Leads -------------------------------------------------------------------
create table if not exists public.leads (
  id                      bigint generated always as identity primary key,
  company_url             text        not null unique,   -- upsert key used by the workflow
  company_name            text,
  summary                 text,
  core_services           text,
  target_personas         text,
  automation_opportunities text,
  phone                   text,
  address                 text,
  email                   text,
  email_a                 text,                          -- draft version A (body only)
  email_b                 text,                          -- draft version B (body only)
  generated_email         text,                          -- final text incl. salutation/signature
  email_subject           text,
  email_version           text,                          -- 'A' or 'B' (chosen in the review form)
  evidence_note           text,                          -- sources checked + verification notes
  status                  text        not null default 'saved',  -- saved | sent
  send_to                 text,
  sent_at                 timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

-- Column added later; safe to run on an existing table:
alter table public.leads add column if not exists email_version text;

create index if not exists leads_status_idx on public.leads (status);

-- 2) Rejected / skipped sites ------------------------------------------------
-- Filled automatically: websites rejected by the industry check and leads
-- skipped in the review form. Prevents suggesting them again for the same industry.
create table if not exists public.rejected_sites (
  domain        text        not null,
  industry      text        not null default '',
  company_name  text,
  reason        text,
  rejected_at   timestamptz not null default now(),
  primary key (domain, industry)
);

-- 3) Security ------------------------------------------------------------------
-- Tables in the public schema are reachable through the Supabase REST API.
-- Enable RLS without policies: the anon/authenticated keys see nothing, while the
-- direct Postgres connection used by n8n (role "postgres") bypasses RLS.
alter table public.leads          enable row level security;
alter table public.rejected_sites enable row level security;

-- 4) Handy queries -------------------------------------------------------------
-- New leads waiting for a decision:
--   select company_name, company_url, email, email_subject from public.leads where status = 'saved' order by created_at desc;
-- Which email version was chosen how often:
--   select email_version, count(*) from public.leads group by 1;
-- Forget a rejected site again:
--   delete from public.rejected_sites where domain = 'example.com';
