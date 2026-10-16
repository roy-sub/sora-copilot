-- Rulebase 2.5.0-rc2: the first version with verified tables in it.
--
-- A new version is a new row, never an update of the old one. Determinations pin the
-- version they were computed against, so 2.5.0-rc1 has to keep existing and keep saying
-- what it was, or a record already in the database would start describing itself with
-- rules it was not computed under.
--
-- `verified` on the row stays false: it means "every table behind this version is
-- verified", and eight still are not. See app/engine/rulebase/sora_2_5/CHANGELOG.md.

insert into public.rulebase_versions (version, changelog, sources, verified, is_current)
values (
  '2.5.0-rc2',
  'igrc, igrc_columns and sail verified against the JARUS SORA 2.5 Main Body release '
  '(JAR_doc_25), cross-checked with the Norwegian CAA SORA 2.5 calculator and JARUS '
  'Annex F. Every regulatory table records the EU adoption (EASA ED Decision '
  '2025/018/R). Eight tables remain seeds, each stating what it needs.',
  jsonb_build_array(
    jsonb_build_object(
      'title', 'JARUS SORA 2.5 Main Body, Release (JAR_doc_25)',
      'url',   'http://jarus-rpas.org/wp-content/uploads/2024/06/SORA-v2.5-Main-Body-Release-JAR_doc_25.pdf'),
    jsonb_build_object(
      'title', 'EASA ED Decision 2025/018/R of 29 September 2025 — AMC and GM to Regulation (EU) 2019/947, Issue 1 Amendment 3',
      'url',   'https://www.easa.europa.eu/en/document-library/agency-decisions'),
    jsonb_build_object(
      'title', 'Norwegian CAA SORA 2.5 calculator (authority implementation, used as corroboration)',
      'url',   'https://training.caa.no/SORA-2.5-calculator/')
  ),
  false,
  true
)
on conflict (version) do nothing;

-- Exactly one current version: the unique partial index enforces it, so rc1 has to be
-- stood down in the same transaction rather than left as a second current row.
update public.rulebase_versions set is_current = false
 where version <> '2.5.0-rc2' and is_current;
