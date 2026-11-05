# DSM cover streaklines

Streakline (dye) images of a forced flat-plate boundary layer, white on black, made for a journal-cover / gallery submission, plus green "PIV-style" wallpapers and a phone Live Photo. Private repository of R. Kelesbekov.

**Not the setup of the DSM article.** The flow is a separate run made only for the picture, so the image is not a reused article figure.

## Flow

- Fortran DSM solver (copy of the campaign source), Re = 5000, plate x = 0.04…5, height H = 1, grid 496 × 176.
- Blasius inlet at x = 0.04. Travelling wave u = 1 + A cos(kx − ωt) on an impermeable moving lid (v = 0), k = 2π, ω = 2π (phase speed 1), A = 0.95. This is a Couette-type channel entry flow.
- Inlet modulation: the campaign band near y = 0.16–0.21, plus the May 2026 MATLAB band under the lid: oscillation fades to zero on y = 0.70–0.80 and grows as ((y − 0.8)/0.2)^3 up to the lid.
- 12 forcing periods; dye from period 2.

## Dye and drawing

- Dye released without pause at the inlet along the May rows (34 rows over the height, 12 extra rows in the upper 30 %, none above 0.95 H) and a thin wall sheet.
- RK4 advection through the saved periods in time order (bilinear in space, linear between the 128 saved phases).
- Point insertion: when two neighbouring particles of one streakline separate by more than 0.006, a new particle is inserted at the Catmull–Rom midpoint and advected with the others (stops at 1/256 of the release spacing).
- Lines drawn with Pillow on a 3× raster and reduced with Lanczos. No generative or AI processing.

## Files

- `images/COVER_2550x3300.png`, `images/COVER_5100x6600.png`: the cover, six strips 1/8 period apart.
- `wallpapers/`: green 532 nm colouring, phone 1290 × 2796 and desktop 3840 × 2400.
- `livephoto/`: one forcing period compressed in time to 3.2 s, 2 s and 1.5 s (MP4), and Live Photo packages `.pvt` (2 s, 1.5 s). Double-click a `.pvt` on a Mac to import it into Photos. iOS lists such synthetic Live Photos in the library but, so far, not as live lock-screen wallpapers.
- `scripts/`: `render_cover_seq.py` (sources, field, time-continuous RK4), `live_wallpaper.py` (dye with point insertion and the Live Photo frames), `make_live_wallpaper.swift` (AVFoundation pair with content identifier and still-image-time track), `wallpaper_piv.py` (green colouring). They need the native period files of the run, which are not in this repository.
