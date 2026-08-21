# Wara — Recovery meeting script (3-minute AI audio, English)

A read-aloud script for a generated audio recording of a short, friendly
recovery call between the client CTO and the project lead, ready to paste
into an AI voice generator. When the recording is ingested through the
meeting-audio path (`specs/019-meeting-audio-ingestion`, see
`demo-wara/AUDIO-INGESTION-TESTING.md`) it gives the Meeting, Tone, and
Commitment readers honest, attributable material for Stage 3 of the demo
(`demo-wara/RECOVERY.md`) — one recurring problem gets fixed, and the two
people talk plainly about why they'd both gone quiet.

> **⚠️ This script was rewritten for the new, simpler Stage 1/2/3 story
> (inventory-sync ticket #209, not the old checkout_api/VTEX/SLA/board
> narrative).** The `.m4a` audio file already shipped in this folder
> (`wara-weekly-sync-recovery.m4a`) was generated from the **old** 4-minute
> script and still talks about the old story. It still works end to end
> as a way to exercise the ingestion pipeline (Whisper transcription,
> pyannote.ai diarization, speaker-roster matching, the Meeting reader) —
> but for it to match Stage 1/2's new fixtures, **regenerate the audio
> from this script** with your AI voice tool of choice and save it back
> to `wara-weekly-sync-recovery.m4a`. Nothing in this repo can synthesize
> audio directly, so that one step is manual. See `RUNBOOK.md`'s Stage 3
> section for exactly how it fits into the walkthrough either way.

> **Language note.** English version (a Spanish original is not included
> in this revision). The speakers self-introduce by full name early so
> the pyannote.ai diarization → roster speaker-matching step can resolve
> them against the loaded Wara profile (`stk_juan`, `stk_fernando`).
> Source citations (ticket number, dates) match the demo fixtures exactly
> so the Meeting reader's `cited_event_ids` land on real events.

---

## Recording parameters (for the AI voice generator)

| Field | Value |
|---|---|
| Duration target | 3:00 (±10 s) |
| Speakers | **Juan Huarachi** — CTO, client (warm, plain-spoken) • **Fernando Juarez** — Dev Lead / project lead, counterpart (calm, straightforward) |
| Language | English (clear, conversational, no jargon) |
| Accent | Neutral / lightly Latin-American English (both speakers are Lima-based; a faint accent is fine, avoid caricature) |
| Tone | Friendly, relieved, no tension. Healthy-account cadence per profile norm: "Fast-paced e-commerce team. Short messages are normal, not hostile." |
| Setting | Friday 17:00 Lima, end-of-week 1:1 video call, recorded with both parties' consent (`series_id: wara-weekly-sync`). |
| Pacing | ~135-145 wpm effective; leave short pauses between speakers and a 1s beat around each commitment so the Meeting reader can cleanly extract it. |
| Voices | Two distinct, identifiable timbres; keep speaker turns short (1-3 sentences) so diarization segments are crisp. |
| Out-of-scope (do NOT include) | Pricing, discounts, contract renewal terms — `wara-profile.yaml` excludes `commercial_negotiation`. Not relevant to this story anyway — keep the call purely about the inventory ticket and the two commitments below. |

---

## Score-driver mapping (how this meeting lowers the score)

| Driver from Stage 1/2 | Finding type it triggered | What this meeting does | Outcome |
|---|---|---|---|
| Ticket #209 reopened Aug 19, inventory sync job failing | `broken_response_promise`, `recurring_issue` | Explain the real cause in plain terms; confirm it's fixed and being watched | Fixed and closed **this morning** |
| Inventory usage dip, CSAT 7 (Stage 1) | `usage_deviation`, `csat_deviation` | Confirm the numbers are back to normal this week | Numbers steady all week; CSAT 9 already filed |
| A week of silence from both sides (Stage 1) | `contact_absence`, `relationship_change` | Both explain why, plainly — no drama, just a busy stretch | Fernando was heads-down fixing it; Juan was swamped with a board cycle |

**Two explicit commitments for the Meeting reader** (each phrased with a
clear verb + owner + deadline so `meeting_commitment` findings emit
cleanly — deliberately kept to two, not five, so this recording doesn't
outweigh the recovery it's meant to demonstrate):

1. Fernando → send a short weekly inventory health-check note — **every
   Friday, starting this Friday**.
2. Juan → raise anything odd in the shared channel right away instead of
   letting it sit — **starting now**.

---

## Script

### 0:00 — Opening / greeting

**Fernando:** Juan, hey — thanks for jumping on. Good timing, actually. I
have an update. Before we start, quick intro for the recording: I'm
Fernando Juarez, project lead on our side.

**Juan:** And I'm Juan Huarachi, CTO at Wara. Good — go ahead, I've been
wanting this update.

### 0:20 — Ticket #209 / inventory sync

**Juan:** So, the inventory thing. Ticket 209. It came back this week,
same problem as before — stock counts not matching the warehouse. What
happened?

**Fernando:** Fair question. The overnight sync job was silently failing
on retries — it looked fine in our dashboard, but it wasn't actually
finishing. That's on us for not catching it sooner. Good news: we found
it, fixed it this morning, and I added a check that pages us the moment
it happens again.

**Juan:** Good. I saw the ticket closed a couple hours ago. Numbers have
looked right all week, actually — no complaints from the team.

### 1:00 — Commitment 1 + CSAT

**Fernando:** Glad to hear it. And going forward — I'll send you a short
note every Friday with the inventory numbers, so you're not finding out
about a problem from your own team first. Starting this Friday.

**Juan:** That's a good habit, thank you. And for what it's worth, I
filed a 9 on the survey this morning. Support's been quick this week too.

### 1:35 — The quiet week

**Fernando:** I noticed we both went quiet for a bit there. I want to be
upfront — that was me heads-down on this exact issue, not avoiding you.

**Juan:** Same, honestly. I had a board cycle that ate my whole week.
Nothing about you or the team — just bad timing on both sides.

**Fernando:** Makes sense. Let's not let it repeat, though.

### 2:05 — Commitment 2

**Juan:** Agreed. From my side — if I see anything odd, I'll drop it in
the shared channel right away instead of sitting on it. Starting now.

**Fernando:** Perfect, that helps a lot. Small things are much easier to
catch early.

### 2:25 — Friendly close

**Juan:** Good call, Fer. Feels like a normal week again.

**Fernando:** It does. Same time next Friday?

**Juan:** Same time next Friday. Talk then.

**Fernando:** Sounds good. Have a good weekend, Juan.

**Juan:** You too. Bye.

---

## Usage with the audio ingestion pipeline

1. Generate the audio from this script with your chosen AI voice tool,
   two distinct voices, ~3 min, English. Save it as
   `wara-weekly-sync-recovery.m4a`, replacing the existing file (which
   was generated from the old, longer script).
2. Drop it into the Drive subfolder — or, per the current local-storage
   path, the local folder — whose name **exactly** matches the consented
   `series_id` (`wara-weekly-sync`) — see `AUDIO-INGESTION-TESTING.md`
   Step 0.
3. Confirm consent is `granted` for that series, then run
   `python -m app.worker --run-once audio` (or `POST
   /api/meeting-audio/refresh`).
4. Run readers (`scripts/run_readers.py`) — expect 2 `meeting_commitment`
   findings citing the new event (Fernando's weekly note, Juan's
   channel-first habit), and no new `tone_deterioration` (the transcript
   is calm throughout).
5. Continue with `RECOVERY.md`'s remaining steps — ingesting
   `wara-recovery-followup.json` and marking select Stage 1/2 findings as
   `false_alarm` from the dashboard — to actually bring the score down.
   **The audio alone does not lower the score** — `meeting_commitment` is
   itself a negative, non-fading finding type
   (`POSITIVE_FINDING_TYPES = frozenset({"commitment_met"})` in
   `backend/app/scoring/domain/entities.py`), so it *adds* a small amount
   of points even in a meeting that goes well. The score comes down
   because the ticket gets closed and because a human reviewer, having
   listened to the meeting, judges the older findings no longer relevant
   — not because the audio event itself is "positive." `RECOVERY.md`
   walks through exactly why and how.

No code is modified by this file; it is a content/script artifact for the
demo only, consistent with the "adds to, does not modify" convention used
throughout `demo-wara/`.
