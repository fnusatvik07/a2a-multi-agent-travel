# AtlasTrip explainer

The 89 second explainer in the project README, as a HyperFrames composition.

```
STORYBOARD.md   the plan: 10 frames, what each one does and how it moves
SCRIPT.md       the locked narration, one line per frame
frame.md        the design system (the `code-editorial` preset)
compositions/   one HTML file per frame, plus the caption track
assets/fonts/   EB Garamond, Inter and JetBrains Mono, so renders are offline
index.html      the assembled timeline
```

## Rebuilding it

```bash
cd videos/atlastrip-a2a-explainer
npm install
npx hyperframes check          # lint, runtime, layout, motion, contrast
npx hyperframes render --quality high --output renders/video.mp4
```

Narration and captions are regenerated from `SCRIPT.md`:

```bash
node <faceless-explainer-skill>/scripts/audio.mjs \
  --script ./SCRIPT.md --storyboard ./STORYBOARD.md --hyperframes . \
  --out ./audio_meta.json --voice am_adam
```

The generated audio, captions and renders are git-ignored; the plan, the design
spec, the frames and the fonts are not, so the composition is reproducible from
what is committed.

## Notes on the build

- Ten frames, each built independently against a bounded packet, then assembled
  with crossfades on four seams.
- Narration is local (Kokoro `am_adam`); there is no music bed.
- Every figure in the video is real: `$3,110.48` of flights, `$298.33` a night
  rejected against a `$280.00` cap, `$189.96` accepted, `$3,688.76` total
  against `$7,600.00` left in the quarter. They come from an actual run of the
  network, not from the script.
- Coral is rationed to four moments in the whole film: the word `cannot`, the
  dependency collision, the policy violation, and the halt. That restraint is
  why those four moments land.
