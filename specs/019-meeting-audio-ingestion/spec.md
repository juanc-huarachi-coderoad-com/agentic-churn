# Feature Specification: Meeting Audio Ingestion

**Feature Branch**: `019-meeting-audio-ingestion`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Audio de reuniones como fuente del score — build the real audio→transcript ingestion path (local storage + OpenAI Whisper) that feeds the existing meeting-transcript evidence pipeline, replace the ad hoc per-item consent flag with an auditable per-series consent record, and support both scheduled polling and an on-demand manual refresh. Audio is discarded immediately after transcription; only encrypted text persists. Intended to be demoable." Revised 2026-08-20: switched the audio source from Google Drive to local storage because Drive's OAuth setup was too difficult to install for the demo; a sample recording is already available at `demo-wara/wara-weekly-sync-recovery.m4a`. The functionality should stay simple and easy to understand — drop a file in a folder, no external account or authorization step.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Meeting evidence appears in the score automatically (Priority: P1)

A CS lead has been documenting client conversations by recording meetings and saving the audio files into a local folder on the machine running the product, the way their team already does today — no separate account to set up, nothing to authorize. Without anyone touching the scoring system, a commitment made in that recording ("we'll have the integration live by Friday") shows up as cited evidence in the client's health score within the same day.

**Why this priority**: This is the entire point of the feature — everything else exists to make this happen safely. The evidence pipeline, the finding type, and the scoring arithmetic this evidence feeds already exist and are unchanged; this story is what turns a recording sitting in that local folder into something the score can see.

**Independent Test**: Place a consented meeting recording in the configured local storage folder, wait for the next scheduled collection cycle, and confirm a transcript-derived finding appears in the client's evidence trace and is reflected in the next score computation, with the audio recording itself gone by the time transcription completes.

**Acceptance Scenarios**:

1. **Given** a new audio recording is present in the configured local storage folder for a meeting series with documented consent, **When** the scheduled collection cycle runs, **Then** the recording is transcribed, discarded, and its transcript is available as evidence exactly the way an example-text meeting transcript is today.
2. **Given** a recording was already transcribed in a previous cycle, **When** the next scheduled cycle runs and the same recording is still present in local storage, **Then** it is not transcribed or scored a second time.
3. **Given** a transcript is successfully produced, **When** it is stored, **Then** only the transcribed text is retained (encrypted, subject to the deployment's existing retention window) and no audio bytes exist anywhere in the system.

---

### User Story 2 - Consent is documented and enforced per meeting series (Priority: P1)

Before any recording from a given recurring meeting (e.g., "Acme Corp — Weekly Sync") can ever be collected, someone with the authority to do so must record that every participant in that series has agreed to be recorded and analyzed. That record is durable and auditable — it says who confirmed consent, when, and for which series — and it can be revoked. Nothing is ever transcribed for a series without an active consent record covering it, and the system can prove that at any point.

**Why this priority**: This is a hard compliance gate, not a nice-to-have — the existing meeting-evidence capability has been withheld from production specifically pending exactly this control. It ships alongside User Story 1, not after it: the collector in Story 1 has no legitimate behavior without this gate existing first.

**Independent Test**: Record consent for a meeting series through the system, confirm the record is retrievable with who/when/which-series detail, revoke it, and confirm a recording belonging to that series is never collected afterward — independent of whether any actual audio collection has run.

**Acceptance Scenarios**:

1. **Given** a meeting series has no consent record, **When** the collector encounters a recording belonging to that series, **Then** the recording is never downloaded or sent for transcription, and this is enforced structurally (not merely skipped by convention).
2. **Given** an authorized user documents consent for a meeting series, **When** they save it, **Then** a durable, timestamped, attributable record is created and is queryable later as an audit trail.
3. **Given** consent for a meeting series is later revoked, **When** the next collection cycle runs, **Then** no further recordings from that series are collected; transcripts and findings already produced before revocation are left exactly as any other retained evidence is (no new deletion behavior is introduced).

---

### User Story 3 - On-demand refresh ahead of a review (Priority: P2)

A CS lead is about to walk into a client renewal conversation and wants the score to reflect a meeting that was recorded an hour ago, not whenever the next scheduled cycle happens to run. They trigger an immediate check from the dashboard and see the result without waiting.

**Why this priority**: Materially improves the feature's usefulness and is the more visible, demoable half of "two modes of execution," but the product delivers real value through scheduled polling alone even before this exists.

**Independent Test**: With a new consented recording present in local storage, trigger the manual refresh action and confirm the same collection-and-transcription behavior as a scheduled cycle happens immediately, without waiting for the next scheduled interval.

**Acceptance Scenarios**:

1. **Given** a consented recording is available in local storage, **When** an authorized user triggers a manual refresh, **Then** the same discovery/transcription/evidence pipeline as the scheduled job runs immediately and completes before returning control to the user.
2. **Given** a manual refresh is triggered while no new recordings are present, **When** it completes, **Then** the user sees a clear "nothing new" outcome rather than an error or a silent no-op.

---

### User Story 4 - Honest degradation when the audio source breaks (Priority: P2)

The configured local storage folder becomes unreadable — it's deleted, unmounted, or its permissions change — or Whisper transcription starts failing. Nobody notices for a week because nothing crashes — the score simply stops incorporating new meeting evidence. When someone does look, the dashboard should have already been telling them: a visible notice that the meeting-audio source is degraded, with the score frozen at its last good value rather than silently going stale or, worse, silently excluding meeting evidence as if it never mattered.

**Why this priority**: Consistent with how every other source in this product already fails (score freezes and coverage is flagged, never silently drifts) — this story is what keeps the audio source honest under exactly that same existing contract, rather than being a special case that erodes trust in the score.

**Independent Test**: Simulate an inaccessible local storage folder (removed, unmounted, or permission-denied) or a transcription failure, run a collection cycle, and confirm the failure is visible in the coverage signal within one cycle while the score is frozen rather than computed on incomplete evidence.

**Acceptance Scenarios**:

1. **Given** the configured local storage folder is no longer accessible (removed, unmounted, or permission-denied), **When** a scheduled or manual collection cycle runs, **Then** the failure is surfaced as a visible, actionable notice and the cycle does not crash or silently produce zero results indistinguishable from "no new recordings."
2. **Given** a specific recording fails to transcribe, **When** the cycle continues, **Then** that recording is skipped without blocking transcription of any other recording in the same cycle, and the failure is recorded.
3. **Given** the audio source is degraded, **When** the score is next computed, **Then** it freezes at its last value with visibly reduced coverage, matching how the system already treats any other source's coverage gap.

### Edge Cases

- A recording's audio is corrupted or in an unsupported format: transcription fails for that item only; it is skipped, logged, and retried on a later cycle rather than blocking the rest of the batch.
- A recording contains no discernible speech (e.g., silence, dead air, a cancelled meeting recorded by mistake): transcription completes with no commitments extracted, which is already a normal, valid outcome for the existing meeting reader.
- A speaker in the recording cannot be confidently matched to a known stakeholder: the segment is kept as evidence but left unattributed rather than guessed — the system never assigns an identity it isn't confident in.
- A recording belongs to a meeting series that has never had any consent decision recorded (neither granted nor revoked): treated identically to "no consent" — it is never collected.
- The same recording is deleted from local storage between discovery and processing: treated as a transient per-item failure for that cycle, not a fatal error for the run.
- A meeting series' consent is revoked mid-cycle, after some of its recordings were already read but before transcription of all of them completes: any recording not yet transcribed for that series is abandoned for that cycle rather than proceeding.
- A folder exists in the configured local storage location whose name matches no known meeting series identifier (a typo, a folder created before its series was registered, or a stray unrelated folder): it is skipped and logged as an unmapped folder — never treated as consented by default, and never surfaced as a false "gap" for a series that was never expected to exist there.
- A recording already successfully processed in a prior cycle is still present in local storage on a later cycle: it is recognized and skipped *before* it is read or re-sent for transcription — not merely prevented from creating a second evidence record after being re-transcribed. Re-transcribing an already-processed recording is itself the outcome being prevented, not just its downstream duplication.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: THE SYSTEM SHALL discover new meeting audio recordings from a configured local storage location on a scheduled, configurable interval, requiring no external account, authorization, or re-authentication step of any kind.
- **FR-002**: THE SYSTEM SHALL also allow an authorized user to trigger an immediate, on-demand collection cycle equivalent to a scheduled one, independent of the configured interval.
- **FR-003**: THE SYSTEM SHALL NEVER download or transcribe a recording belonging to a meeting series that does not have an active, documented, all-party consent record at the time of collection — this check SHALL be enforced at collection time on every cycle, not only when consent was first granted.
- **FR-004**: THE SYSTEM SHALL maintain a durable, append-only, queryable audit record of consent per meeting series, capturing who documented it, when, and its current status (granted or revoked).
- **FR-005**: THE SYSTEM SHALL allow an authorized user to document consent for a meeting series and to revoke it; a revocation SHALL take effect for every collection cycle from that point forward.
- **FR-006**: THE SYSTEM SHALL transcribe each collected recording to text, including which participant spoke each segment where that can be determined with confidence.
- **FR-007**: THE SYSTEM SHALL leave a spoken segment's speaker unattributed rather than assign a guessed identity when it cannot confidently match the segment to a known meeting participant.
- **FR-008**: THE SYSTEM SHALL discard the original audio content after transcription completes — successfully or not — such that no audio bytes are retained anywhere in the system beyond the single processing pass.
- **FR-009**: THE SYSTEM SHALL emit each successfully transcribed recording into the existing meeting-evidence pipeline in the same shape the system's example-text meeting transcripts use today, requiring no changes to identity resolution, redaction, encryption, evidence citation, or score computation.
- **FR-010**: THE SYSTEM SHALL store only the transcribed text (never the audio) as evidence, encrypted, and subject to the deployment's existing message-body retention window.
- **FR-011**: THE SYSTEM SHALL NOT re-transcribe or re-score a recording that was already successfully processed in a prior cycle. This SHALL be checked before a recording is downloaded or sent for transcription — not only enforced as a later step that discards a duplicate result — since the recording, not merely its resulting evidence record, is what must not be re-processed.
- **FR-012**: THE SYSTEM SHALL verify that the configured local storage location is accessible (exists and is readable) as part of every scheduled and manual collection cycle, and SHALL surface a visible, actionable notice — distinguishable from "no new recordings found" — when it is not.
- **FR-013**: WHEN the local storage location cannot be reached, an individual recording fails to transcribe, or the local storage location is inaccessible, THE SYSTEM SHALL continue processing every other unaffected recording in the same cycle rather than aborting the whole cycle.
- **FR-014**: WHEN the audio source is degraded across a collection cycle, THE SYSTEM SHALL freeze the score at its last computed value and visibly flag reduced coverage, consistent with how the system already handles any other source's coverage gap, rather than silently omitting meeting evidence or computing on incomplete data.
- **FR-015**: THE SYSTEM SHALL determine which client account and meeting series a discovered recording belongs to by its containing local storage folder, using a one-folder-per-meeting-series organization convention (folder name = series identifier) that maps directly to the same series identifier used elsewhere in the system. A folder whose name does not match any known series identifier SHALL be skipped and logged, never treated as an implicitly consented or newly-created series.
- **FR-016**: THE SYSTEM SHALL restrict documenting or revoking meeting-series consent to the CS lead who owns the client relationship, exposed as a dashboard control — the same role and surface already trusted for other client-affecting actions (feedback verdicts, profile edits) in this product.

### Key Entities *(include if feature involves data)*

- **Meeting Series Consent Record**: The auditable record that gates collection for one recurring meeting series — which series it covers, who documented it and when, and its current status (granted or revoked). New; does not exist today. Every collected recording is checked against this record at collection time.
- **Meeting Recording**: The audio artifact discovered in local storage for one occurrence of a meeting series. Transient by design — it exists only for the duration of a single collection-and-transcribe pass and is never persisted once that pass completes.
- **Meeting Transcript**: The text produced by transcribing one recording, including per-segment speaker attribution where confidently known. This is the existing evidence artifact the current meeting-evidence pipeline already consumes; this feature is a new way of producing it, not a new shape for it.
- **Collection Cycle**: One run of the discovery/transcribe/emit process, whether triggered on schedule or on demand — what it found, what it processed, what it skipped, and any failures, so a degraded audio source is diagnosable after the fact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A commitment made in a consented, recorded meeting is visible as cited evidence in the client's score within one scheduled collection interval of the recording becoming available, with no manual step required.
- **SC-002**: Zero recordings are ever transcribed for a meeting series lacking an active, documented consent record — verified with 100% consistency across testing and audit review of the consent record.
- **SC-003**: An authorized user can force an immediate evidence update ahead of a scheduled cycle, and see it reflected in the evidence trace, in under one minute of triggering the refresh (excluding transcription time for very long recordings).
- **SC-004**: No audio content is recoverable from the system at any point after a collection cycle completes — verified by inspecting system storage after processing.
- **SC-005**: When the audio source becomes unreachable, a visible degradation notice appears within one collection interval, and the score never silently reflects a state as if the outage weren't happening.
- **SC-006**: Every piece of speaker-attributed meeting evidence names a real, known stakeholder; zero instances of a fabricated or guessed speaker identity occur in evidence shown to a CS lead.

## Assumptions

- This feature adds the real, first non-simulated audio collector this product ships (local file storage + a transcription service, OpenAI Whisper); every source before it has run against a committed example fixture standing in for a live source. The existing collector interface, envelope shape, identity resolution, redaction, encryption, coverage reporting, and score-freeze behavior are all reused unmodified — this feature is additive at the ingestion boundary only, consistent with the existing "meeting evidence already works end-to-end with example text" state of the product.
- A single configured local storage location (one filesystem directory, organized one-subfolder-per-meeting-series) is sufficient per deployment, consistent with this product's existing single-client-per-deployment operating model — this feature does not need to support multiple simultaneous storage locations within one deployment. Choosing local storage over a cloud drive removes the OAuth/app-registration setup step entirely: an authorized user places a file in the right folder and it is picked up on the next cycle, with no external account to configure or re-authorize.
- The scheduled polling interval defaults to a conservative, configurable number of hours (not sub-hourly); exact timing is a deployment-configuration detail, not a scope-defining decision, and is tuned after the demo based on how fresh evidence needs to be in practice.
- Speaker attribution matches each diarized segment against the client account's existing stakeholder roster (the same roster every other source's identity resolution already draws on) as its candidate name set — not a separate, per-meeting-occurrence attendee list, which nothing in the system currently captures. A deployment's stakeholder roster is small (single-digit to low-double-digit people) and bounded per account, so matching against the whole roster rather than a per-occurrence subset is a reasonable, implementable default; a segment that doesn't confidently match any roster name stays unattributed exactly as FR-007 requires. This feature does not introduce a second, parallel identity system.
- A previously collected transcript or finding is not deleted or altered when its meeting series' consent is later revoked; it remains subject to the same retention/crypto-shredding window every other piece of message-body evidence already follows. Revocation only prevents future collection.
- This feature is intended to be demonstrated end-to-end (a recording placed in local storage becoming visible as score evidence) within the project's existing demo environment and timeline. A sample recording (`demo-wara/wara-weekly-sync-recovery.m4a`) is already available to exercise the path without needing to produce new audio.
