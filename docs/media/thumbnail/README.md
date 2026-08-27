# Thumbnails

Three concepts for the explainer, all 1280x720, all checked at 320x180 because
that is the size a thumbnail is actually judged at in a feed.

| | Concept |
|---|---|
| `thumbnail-c.png` | **The cast.** The five agent glyphs from the film as the subject, connected by the wire they talk over, with one message in flight. Recommended. |
| `thumbnail-b.png` | **The constraint.** Leads on "they can't run in one process" with the framework marks beneath. |
| `thumbnail-a.png` | **The summary.** Type-led, framework marks as a footer. |

## Design notes

The film's palette is warm cream, a single terracotta accent and a lot of white
space. That is right for an editorial explainer and wrong for a thumbnail: it
disappears in a feed of saturated images. All three invert to the ink ground and
keep coral as the one accent, so they stay recognisably part of the same project
while surviving the context they appear in.

The agent glyphs are lifted from the film itself rather than redrawn, but their
stroke goes from 2 to 3.6 on the 64-unit grid. A 2px stroke is invisible after a
4x downscale.

## Regenerating

The builders are throwaway scripts, not part of the project's toolchain; the
PNGs are the artifact. The glyphs come from
`videos/atlastrip-a2a-explainer/compositions/frames/12-close.html`, the brand
marks from `videos/atlastrip-a2a-explainer/assets/logos/`, and the fonts from
`videos/atlastrip-a2a-explainer/assets/fonts/`.
