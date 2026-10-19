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

**Not used:** YouTube. Ripping audio breaks YouTube's terms. "Topic" channels
(e.g. "U.S. Drill Sergeant Field Recordings – Topic") are commercial albums, so
copying them onto this public site isn't allowed either. If commercial
cadence is ever wanted, buy DRM-free albums and host them privately (not in
this public repo).

## What's in the app (Oct 2026)

13 clips, 19.7 min, each a complete sung call-and-response running cadence,
150–171 spm (mostly 160s). The Army 10-Mile Run clip (6:50–8:00) was put
back after Mat listened; its transcript had been unreadable. That is everything usable that was found in about
250 DVIDS/Commons videos. DVIDS searches for cadence, jody, moto/motivational
run, formation/unit/battalion/brigade/division/regimental run, cadence
contest/competition are exhausted. Freesound has nothing useful.

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
   readings got them mislabeled as 152–155 spm. They're excluded.
3. **Fragments.** The detector loses the beat during call-and-response pauses
   and cuts songs into slices. Mat wants complete songs, not 24 s pieces.
4. **Transcripts aren't ears.** Speech recognition handles one caller well
   but turns a whole formation singing into "oh yeah… let him, let him" or
   gibberish. An unreadable transcript is a reason to ask Mat to listen
   (give him the DVIDS link and timestamps), not a reason to reject.
5. **Disk.** Source videos for ~250 sources came to 17 GB. Keep them out of
   Dropbox (`CADENCE_STAGING`) and delete them when done.

## How to add a new source properly

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
