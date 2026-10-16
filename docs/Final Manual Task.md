# Final Manual Task — done

**Status: complete.** You added `jarus-rpas.org` and `easa.europa.eu` to the cloud
environment's allowed domains, I transcribed the remaining tables from the official
text, and the app no longer carries an UNVERIFIED warning anywhere.

This file is kept as the record of what that one minute of settings bought, and of the
one thing I decided differently from the plan once I could read the source.

---

## 1. What the task was

SORA Copilot answers a regulatory question from **14 tables of numbers**. Six of them
had been checked against the published documents. Eight had not, because the cloud
container I work in could not open the two websites those documents live on, and I will
not guess a number in a compliance product — a plausible wrong number is worse than a
visible gap, because somebody flies a drone on it.

You added the two domains. That is all it needed.

## 2. What I did with the access

I did **not** use jarus-rpas.org. When I opened it, its TLS certificate did not match
the site: it was self-signed, issued to `C=CN, CN=unknown, emailAddress=unknown@wts`.
That is not a JARUS certificate, and a document fetched over a connection like that
cannot be trusted to be the document — which is the whole point of transcribing from a
primary source. So I left it alone and told you rather than quietly using it.

Everything came from EASA instead, which is the better source anyway:

- **EASA ED Decision 2025/018/R of 30 September 2025** adopted the whole SORA 2.5
  package as AMC and GM to Regulation (EU) 2019/947.
- It is consolidated into the **Easy Access Rules for Unmanned Aircraft Systems,
  revision of June 2026** — a 617-page book, downloaded over a verified TLS connection.

In the EU this is not a secondary source. "JARUS recommends" is a weaker citation to an
EU authority than "this is the AMC to the Regulation", so every table now cites the
Easy Access Rules and records the ED Decision that adopted it.

## 3. What changed

| | Before | Now |
|---|---|---|
| Tables verified | 6 of 14 | **14 of 14** |
| Verdict screen | "8 of the regulatory tables… are still transcribed from a seed" | No banner |
| Exported dossier | "must not be submitted to an authority" on every page | Submittable |
| Citations | Document and section | Document, section **and page number** |
| Rulebase version | 2.5.0-rc.2 | **2.5.1** |

Seven of the eight unchecked tables turned out to be wrong, and six of those change an
answer the product gives. If you demonstrated the app to anyone on the old numbers,
these four are the ones worth mentioning:

1. **A flight in a transponder mandatory zone got the wrong air risk class.** The air
   risk table had ten branches; the official Table C.1 has twelve. The Mode-S Veil /
   TMZ classes and the above-FL600 class were missing outright.
2. **Strategic air-risk mitigation was too generous.** The old table lowered the air
   risk by one class for anyone who *claimed* a mitigation. Table C.2 sells that
   reduction for a **demonstrated** local traffic density, not for a claim — and where
   it does apply, it can be worth two classes rather than one. The worked example moved
   from SAIL III to SAIL IV until a demonstrated density rating was supplied.
3. **Step #8 now reaches an answer.** Containment was a two-tier guess with an open
   question recorded against it. S.4.8.1(c) names three levels — low, medium, high —
   so the Dutch regulator's basic/enhanced was a national exemption, not SORA 2.5. The
   app computes a level now instead of telling the operator to assess it themselves.
4. **OSO#04 was understated.** It read low/medium/high at SAIL IV/V/VI; the adopted
   Table 14 says medium/high/high.

Also corrected, without moving a verdict on the worked example: M1(B) operational
restrictions were missing from the mitigation table entirely (−1 at medium, −2 at high);
the contingency volume is the sum of five terms rather than one position error, and the
ground risk buffer is H_CV + CD/2; and the altitude band is **150 m**, not the 152.4 m
that PLAN.md had decided by converting 500 ft — Table C.1 writes every altitude row as
"150 m (~500 ft) AGL", so 150 m is the figure and 500 ft is the approximation of it.

One table, the TMPR mapping, was already right. That was luck rather than method, and
it is now the table's own four rows rather than a monotone rule that happened to agree.

## 4. What is actually left for you

Three things, none of them code:

1. **Fill in the `.env` files** — [ENV Example](./ENV%20Example.md) lists every
   variable, and [Third Party Setup Guide](./Third%20Party%20Setup%20Guide.md) walks
   through getting each value.
2. **Deploy the backend to Render** — [Deployment Guide](./Deployment%20Guide.md),
   Part 1.
3. **Host the frontend on Cloudflare Pages or Hostinger** — Deployment Guide, Part 2,
   which ends with the one command that produces the folder you upload.

The code is complete, the tests pass, the media ships with the build, every table is
transcribed from the adopted text, and the engine computes every determination from
rules rather than from a language model.
