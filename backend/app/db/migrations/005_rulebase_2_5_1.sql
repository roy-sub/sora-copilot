-- Rulebase 2.5.1: the first version with every table transcribed from the adopted text.
--
-- A new version is a new row, never an update of the old one. Determinations pin the
-- version they were computed against, and three of the corrections in this release
-- change a verdict, so 2.5.0-rc1 and -rc2 have to keep existing and keep saying what
-- they were — otherwise a stored record would start describing itself with rules it was
-- not computed under.
--
-- `verified` is true for the first time: every table behind this version names the
-- document, section and page it was transcribed from.

insert into public.rulebase_versions (version, changelog, sources, verified, is_current)
values (
  '2.5.1',
  'Every table transcribed from the EASA Easy Access Rules for UAS, revision of June '
  '2026, which incorporates ED Decision 2025/018/R — the SORA 2.5 package as AMC and GM '
  'to Regulation (EU) 2019/947, Issue 1, Amendment 4. Six of the eight unchecked tables '
  'were wrong: the ARC tree was missing the transponder-mandatory-zone and above-FL600 '
  'categories, the residual ARC was giving away a class for a claim rather than a '
  'demonstrated density, containment is six tables rather than one row, Table 5''s '
  'M1(B) mitigation was absent, OSO#04 was a level low at SAIL IV to VI, and the '
  'altitude band is 150 m rather than 152.4 m.',
  jsonb_build_array(
    jsonb_build_object(
      'title', 'EASA Easy Access Rules for Unmanned Aircraft Systems (Regulation (EU) 2019/947 and Regulation (EU) 2019/945), revision of June 2026',
      'url',   'https://www.easa.europa.eu/en/downloads/110913/en'),
    jsonb_build_object(
      'title', 'ED Decision 2025/018/R of 30 September 2025 — AMC and GM to Regulation (EU) 2019/947, Issue 1, Amendment 4',
      'url',   'https://www.easa.europa.eu/en/document-library/agency-decisions')
  ),
  true,
  true
)
on conflict (version) do nothing;

-- Exactly one current version: the unique partial index enforces it, so the previous
-- one has to be stood down in the same transaction.
update public.rulebase_versions set is_current = false
 where version <> '2.5.1' and is_current;
