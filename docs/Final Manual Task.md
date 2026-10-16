# Final Manual Task

**Time needed:** about one minute.
**What it is:** ticking two boxes in a settings page so I can read two websites.
**Is the app broken without it?** No. It works, it is honest, and you can launch. This
closes the last gap between "working" and "verified".

---

## 1. The problem, in plain words

SORA Copilot's job is to answer a regulatory question: given a drone, a place and a
flight, what is the risk class, and what must the operator prove? Those answers come
from tables of numbers that are published by two organisations:

- **JARUS** — the people who wrote the SORA 2.5 method. Their documents live at
  **jarus-rpas.org**.
- **EASA** — the EU aviation regulator, who formally adopted SORA 2.5 into EU law in
  September 2025. Their documents live at **easa.europa.eu**.

The app has **14 of these tables**. Think of each one as a page out of a rulebook.

- **6 are finished.** I checked their numbers against the published documents and
  against the Norwegian aviation authority's own calculator, which implements the same
  tables. They agree, line for line.
- **8 are not.** They currently hold sensible placeholder numbers.

Those 8 are not finished because **this computer I am working on is not allowed to open
those two websites.** It runs in a locked-down cloud container, and its network settings
only permit a short list of sites. jarus-rpas.org and easa.europa.eu are not on the
list, so when I try to download the PDFs, the connection is refused.

I could not guess the missing numbers. In a compliance product, a plausible-looking
number that is wrong is worse than an obvious gap: someone could fly a drone on it. So
the app says, out loud and in writing, which tables are unfinished.

## 2. What the app does about it today

Nothing is hidden. Right now:

- The **verdict screen** shows a strip saying how many of the tables behind *that*
  determination are unfinished, with a button that names each one.
- The **exported dossier** repeats it on the cover and on every page, and says the
  document must not be submitted to an authority.
- The **settings screen** lists exactly which tables are outstanding and which document
  would close each one.

This is the correct behaviour, and you can ship it. A drone operator can use the app to
plan, to explore options and to see the reasoning — they just cannot file the output
with their aviation authority yet.

## 3. What I need you to do

You are going to add two website addresses to a list of sites this cloud container is
allowed to visit.

### Step by step

1. Open **claude.ai** in your browser and open this project's Claude Code session —
   the same place you are reading my messages.
2. Look at the **title bar at the top of the session**. There is a menu there for the
   **cloud environment** this session runs in. Click it.
3. Click **Edit**.
4. Find the setting called **Network access**.
5. You will see a list called **Allowed domains**. (If the access level is set to
   something stricter, choose **Limited** or **Custom** first — "Allowed domains" only
   appears on those levels.)
6. Add these two lines, one at a time:

   ```
   jarus-rpas.org
   easa.europa.eu
   ```

7. Leave the box **"Allow package managers"** ticked if it is there. Unticking it would
   break the build.
8. Save.

The official instructions, if the screen looks different from the above:
https://code.claude.com/docs/en/cloud-environments#network-access

### Then tell me

Send me a message saying it is done — "domains added" is enough. I will:

1. Download the official JARUS SORA 2.5 documents and the EASA decision text.
2. Transcribe the remaining 8 tables from them, with a page reference on each.
3. Re-run the engine's worked examples to make sure nothing changed that should not have.
4. Push the result and tell you what moved.

It is one working session, not a project.

## 4. What changes when it is done

| | Today | After |
|---|---|---|
| Tables verified | 6 of 14 | 14 of 14 |
| Verdict screen | "8 of the regulatory tables… are still transcribed from a seed" | No banner |
| Exported dossier | "must not be submitted to an authority" on every page | Submittable |
| Citations | Document and section | Document, section **and page number** |

## 5. "Can I launch without doing this?"

Yes — with one caveat you should decide on deliberately.

**Safe to launch now:** the app as a planning and exploration tool. Everything works.
Every number it shows is traceable to a rule, every unfinished table says so, and
nothing claims to be verified when it is not.

**Not safe to launch now:** the app as something a drone operator files with their
aviation authority. The app already refuses to pretend otherwise — that is what the
banners are for.

If you would rather not touch the settings at all, the alternative is to send me the
documents yourself: download the SORA 2.5 Main Body and Annexes A–F from jarus-rpas.org
and upload them to a session. That works equally well. The domain allowance is simply
quicker.

---

## 6. The other sentence I wrote, explained

> *"A table can no longer claim `verified: true` without a `basis:`, and the loader
> refuses an unverified table without a `needs:`."*

In plain words: **each of the 14 tables is a small file, and each file now has to answer
the question "how do you know?" in writing.**

- A table that says *"I am verified"* must also carry a sentence saying **what was
  checked, against which document**. If that sentence is missing, the app refuses to
  start. Verification cannot be switched on by changing one word.
- A table that says *"I am not verified yet"* must carry a sentence saying **what is
  still missing** — which document, which figure, which open question. That sentence is
  what the operator reads in the warning strip.

The point of the second one: "something here is unverified" is not useful to anybody.
"Figure 4 of the Main Body, all thirteen branches" tells you exactly what to go and get.

> *"The verdict banner and the dossier banner now count the open tables instead of
> condemning the whole rulebase."*

The warning used to say *the regulatory tables have not been checked* — all of them.
That became untrue once six were checked. A warning that is **more alarming than the
truth** is dangerous in a specific way: people learn it is always on, and stop reading
it. So it now counts: *"8 of the regulatory tables behind this determination are still
transcribed from a seed."* When the number reaches zero, the banner disappears by
itself — nobody has to remember to remove it.

---

## That is the whole list

After this, and the credentials in
[Third Party Setup Guide](./Third%20Party%20Setup%20Guide.md) and the deployment in
[Deployment Guide](./Deployment%20Guide.md), there is nothing else outstanding. The code
is complete, the tests pass, the media ships with the build, and the engine computes
every determination from rules rather than from a language model.
