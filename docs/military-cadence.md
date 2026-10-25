# Military cadence: where it comes from and what not to repeat

Read this before adding or re-importing military cadence clips.

## Where the audio comes from

- **DVIDS** (dvidshub.net, Defense Visual Information Distribution Service): the
  US military's official public media site. Units upload video of their runs,
  ceremonies and cadence contests. Made by service members on duty, so US
  Government work: public domain. Credit the videographer and unit anyway.
- **Wikimedia Commons**: a few official U.S. Army "cadence" videos (Rock Steady,
  Old Lady) that the Army released under CC BY and someone mirrored to Commons.

The app only uses the audio. `tools/fetch_cadence.py` downloads each video
listed in `tools/cadence-sources.json`. `tools/import_cadence.py` cuts the
listed stretch out as an MP3 into `public/cadence/`.

- **Mat's cadence library** (Dropbox, `local:` sources): recordings Mat
  collected and edited himself (see "Dropbox batch" below). **Mat holds the
  rights to his library; everything in it goes in the app.** Don't second-guess
  that from folder names or catalog `license` text.

## What's in the app (Oct 20, 2026)

111 clips, 350 min:
- 13 from DVIDS/Commons: complete sung running cadences, 153–171 spm. That is
  everything usable in about 250 DVIDS/Commons videos; DVIDS searches for
  cadence, jody, moto/motivational run, formation/unit/battalion/brigade/
  division/regimental run, cadence contest/competition are exhausted.
  Freesound has nothing useful. The Army 10-Mile Run clip (6:50–8:00) was put
  back after Mat listened; its transcript had been unreadable.
- 98 from Mat's library: every file except exact duplicates, whole files as
  he edited them. Running pace 150–194; marching and drum cadences (105–149)
  sit under the "Marching" heading on the home page.

## What went wrong, so it isn't repeated

1. **The beat detector can't hear words.** `steady_segments` keeps any stretch
   with a steady beat. In DVIDS videos that is mostly not cadence: graduation
   speeches over a band, PT rep counting, crowd yelling, footsteps, stock
   music. An unreviewed bulk import of ~200 videos produced 184 clips; nearly
   all were junk, most of them 24–32 s fragments. It was pushed live before
   anyone checked it, then removed.
2. **Marching cadence isn't running cadence.** The Coast Guard and drill
   sergeant contest songs (Victory, Your Son Is Gone, Old Man James, In the
   Coast Guard…) are called at ~110–120 steps/min. `detect_bpm.to_cadence`
   only doubles or halves a tempo, so 115 never fits 150–189, and stray
   readings got them mislabeled as 152–155 spm. `clip_tempo` now labels a
   mostly-not-running clip with its real step rate, so marching tracks land
   under "Marching" instead of posing as runs.
3. **Fragments.** The detector loses the beat during call-and-response pauses
   and cuts songs into slices. Mat wants complete songs, not 24 s pieces.
4. **Transcripts aren't ears.** Speech recognition handles one caller well
   but turns a whole formation singing into "oh yeah… let him, let him" or
   gibberish. An unreadable transcript is a reason to ask Mat to listen
   (give him the DVIDS link and timestamps), not a reason to reject.
5. **Disk.** Source videos for ~250 sources came to 17 GB. Keep them out of
   Dropbox (`CADENCE_STAGING`) and delete them when done.

## How to add a new source properly

For a file from Mat's library: add a `local:` entry with `"clips": [[0, 100000]]`
(the whole file), then step 5 below. The review steps are for raw video.

1. Add it to `tools/cadence-sources.json` and run
   `fetch_cadence.py <source>` (with no argument it fetches every source that
   isn't rejected).
2. Check it's a sung cadence: listen, or transcribe it (faster-whisper) and look
   for lines echoed back by the formation. If the transcript is unreadable,
   ask Mat to listen.
3. Check it's at running pace: the tempo should read about 150–189 spm, or
   75–95 (one beat per two steps), across most of the clip. ~115 = marching.
4. Write the exact start/end seconds of the whole song as `"clips"`, or a
   `"reject"` reason. The importer follows these; only unreviewed sources fall
   back to auto-detection.
5. Delete that source's line from `tools/cadence-tracks.json` if it was
   checked before, run `import_cadence.py`, then delete the downloaded videos.

Quality over quantity: Mat would rather have fewer real cadences than many
that waste his time sorting junk.

## Dropbox batch (Oct 2026): Mat's turnover notes

A separate batch Mat assembled outside this repo. Recorded here as he handed
it over; ingestion results follow in the next section.

### Where the files are
Dropbox (local sync: `C:\Users\mamer\Dropbox\Music\Military Cadences\`):
- `Called Cadences\` – 38 MP3s, official/public-domain sources (sung/called
  cadences, mix of running and marching tempo)
- `Drum Cadences\` – 13 MP3s, service-band drum cadences (not running
  material; here for completeness)
- `Running Cadences (Unofficial)\` – 58 MP3s, running cadences from individual
  uploads; the main batch of interest
- `_catalog.csv` covers Called + Drum (51 rows); `_catalog_unofficial.csv`
  covers Running Cadences (Unofficial) (58 rows)

Both CSVs have the same columns: file, branch, title, type, tempo_bpm,
tempo_class, duration_s, source, license, orig_lufs, orig_peak_dbfs, trimmed,
verification.
- `source` = origin + ID (e.g. "YouTube @USArmy 3Cs4Bbu0ZwA", "Wikimedia
  Commons …", "archive.org <identifier>")
- `license` = "US Gov work" / "Public domain" / "Uploader" / "Uploader;
  possibly a commercial album rip"
- `tempo_bpm` / `tempo_class` = automated librosa estimate, folded into
  100–220 and classed running (≥150), marching (≤135), ambiguous. A hint, not
  ground truth.
- `verification` = what was confirmed by speech-to-text transcript, plus what
  was trimmed.

### How they were obtained
- Discovery: YouTube search (yt-dlp, ~40 queries + official service
  channels), Archive.org advancedsearch API, Wikimedia Commons search.
- Official set: U.S. Army / Marines / Navy / Air Force / Coast Guard / DVIDS /
  service-band YouTube channels, Commons DoD files, Archive.org items.
  Commercial cadence albums (Jonathan Michael Fleming, Bob Soldier, Armed
  Fitness, Documentary Recordings, Double Time Records, "Run to Cadence with
  the US Marines") were deliberately excluded.
- Unofficial set: recordings uploaded by individual soldiers/family/fans. A
  few are flagged in `license` as probable rips of commercial
  cassettes/albums (TheScribe114, Half Right Face Productions, Fuhq Ewe).
- Download: yt-dlp bestaudio → WAV; Commons/Archive files downloaded directly.
- Every candidate was analyzed (ffprobe, EBU R128 loudness, silence ratio,
  faster-whisper transcript, librosa tempo) and ~90 candidates were rejected
  as narration/interviews, marching-tempo, destroyed audio, or <30 s. Mat then
  hand-deleted a further ~8 after listening.

### How they were edited
- Encoded to MP3 256 kbps, 44.1 kHz stereo, with ID3 tags: title,
  artist=branch, album="Military Cadences", genre=Cadence,
  comment=source+license.
- Loudness normalized with ffmpeg loudnorm to −16 LUFS integrated, −1.5 dBTP,
  LRA 11 (several sources were clipped at +1 to +3 dBFS; a couple were very
  quiet).
- Dead air trimmed at both ends in two passes: (1) level-based, (2)
  voice-band-energy based (catches tape rumble/hum intros at full level). Trim
  amounts per file are in `verification`. Fades: 0.3 s in, 1.5–2 s out. Files
  that went through pass 2 were re-encoded once from the pass-1 MP3 (one extra
  lossy generation).
- One file (Army – 70th BSB Battalion Run) was cut to its first 12:20 to drop
  speeches.
- No pitch/tempo changes, no EQ, no noise reduction.

## Dropbox batch: ingestion results (Oct 20, 2026)

**Duplicates of what the app already had** (audio fingerprint, sliding
loudness-envelope correlation 0.79–0.94, plus source IDs):
- Airborne Cadence 2019 = Army – Airborne Cadence (C-130 Rolling Down the
  Strip) = Army – Airborne Cadence (Here We Go) = Army – U.S. Army Airborne
  Cadence (three uploads of one recording)
- Old Lady Cadence, Rock Steady Cadence, Coast Guard Turn It Up, Coast Guard
  High Side Right Side
- Already rejected as marching: Your Son Is Gone, Upon the Water, Coast Guard
  on the Scene, In the Coast Guard, Fort Jackson BCT Part 25

**Duplicates inside the batch:** Hard Work Cadence (archive.org) = Hard Work
(Military.Cadences); Rock Steady (Military.Cadences) = US Airborne Cadence
Rock Steady (a different recording from the Army's); MCRD San Diego Cadence
Calling Contest = Drill Instructor Cadence Calling Contest (same audio,
catalog labeled one running and one marching); Cadence All Day = Marching
Cadence (Left Right Left); Hard Work – Live 10 Minutes ≈ Hard Work – Live
Running Cadence.

**Pace, measured with the app's detector** (share of 12 s readings at
150–189 spm): disagrees with the catalog on Fort Jackson 1-61 Family Day and
MCRD San Diego contest (catalog: running; measured: marching ~115) and Basic
Training Cadence (catalog: marching; measured: mostly running, 160). Mixed,
needs an ear: 70th BSB Battalion Run, Hungry as a Hound Dog, Left Your Left,
Rock Steady – Ft McClellan 1987, Saw an Old Lady, Marine Moto Run, both Best
Cadence Caller files. The other 50 unofficial files measure clearly running
(152–185 spm).

**Added to the app:** all 98 non-duplicate files (Called, Drum and Running
Cadences), whole, as source type `local:` in `cadence-sources.json`
(`fetch_cadence.py local:` copies them from the library; the importer
re-encodes to the app's 96 kbps mono). The 11 exact duplicates above were
skipped, keeping one copy of each. Mat holds the rights to the library.

**Mistake made here, don't repeat:** the first pass added only 3 files after
reading the catalog's `license` column and the "(Unofficial)" folder name as
licensing limits. Mat has the rights; the library goes in whole.

## Purchased album (Oct 25, 2026)

Mat bought "50 Running Cadences of the U.S. Military, Vol. 2" (U.S. Drill
Sergeant Field Recordings, 2016) from Amazon Music. Unzipped into the library at
`Music\Military Cadences\Purchased\U.S. Drill Sergeant Field Recordings\…` and
added whole as `local:Purchased/…` sources (`amz-drill-sgt-vol2-NN-*.mp3`).
No duplicates of existing clips (fingerprint ≤ 0.60). Measured: 41 at running
pace (156–171), 9 marching (115–140: Jody, Here We Go Again, Everywhere We Go,
All the Way, I Heard That in the Navy, Hey Apache, and the three "Marching…"
tracks). App total: 161 military tracks, 423 min. The download zip stays out
of git (`*.zip` in `.gitignore`).
