"""
Says what kind of difference each differing area is, the way a tester would describe it:

    position   the element is there but moved ("moved 8 px right and 5 px down")
    size       the element is bigger or smaller ("width 120 -> 150 px")
    colour     the same shape in another colour ("#E77817 -> #C23029")
    content    text, an icon or a picture is different, or the element is present in only one of the two images

    regions = describe(baseline_image, actual_image, regions, pixel_tolerance)    # adds "kind" and "detail" to each region

A design or reference image compared with the real screen differs in many tiny ways (font smoothing); this tells the large
meaningful ones apart: a button that is the wrong colour, a field that is out of line.
"""
import numpy
from PIL import Image

PAD = 16                  # context around the area, so a moved element is still inside the crop
MAX_SHIFT = 24            # how far an element may have moved and still be recognised as "moved"
MAX_SEARCH_PIXELS = 60_000       # larger areas are not searched for a shift (a picture, a photo)
LOSSY_COLOUR_NOISE = 30   # a JPEG design: a colour shift this small, on an area of the same shape, is compression noise, not a defect
MIN_MATCH = 0.2           # share of what appeared that one shift must explain to call the area "moved" ...
PEAK_OVER_AVERAGE = 3.0   # ... and it must stand out clearly from what the other shifts explain by chance
MAX_CLASSIFIED = 25


def _crop(array, region: dict):
    height, width = array.shape[:2]
    left, top = max(region["x"] - PAD, 0), max(region["y"] - PAD, 0)
    right, bottom = min(region["x"] + region["width"] + PAD, width), min(region["y"] + region["height"] + PAD, height)
    return array[top:bottom, left:right].astype(numpy.int16), (left, top)


def _hex(color) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(int(max(0, min(255, round(float(channel))))) for channel in color))


def _different(first, second, tolerance: int):
    return numpy.abs(first - second).max(axis=2) > tolerance


def _background(crop):
    """The most common colour on the border of the crop: what the element sits on."""
    border = numpy.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    values, counts = numpy.unique(border.reshape(-1, 3), axis=0, return_counts=True)
    return values[counts.argmax()]


def _ink_box(crop, tolerance: int):
    """(left, top, width, height) of everything that is not the background, or None."""
    ink = numpy.abs(crop - _background(crop)).max(axis=2) > tolerance
    rows, cols = numpy.nonzero(ink)
    if not len(rows):
        return None
    return int(cols.min()), int(rows.min()), int(cols.max() - cols.min() + 1), int(rows.max() - rows.min() + 1)


def _edges(crop):
    gray = crop.mean(axis=2)
    return numpy.abs(numpy.diff(gray, axis=0))[:, :-1] + numpy.abs(numpy.diff(gray, axis=1))[:-1, :]


def _shift_match(first, second, tolerance: int):
    """
    (dx, dy, share explained, average share of all shifts) of the shift that makes `first` match `second` best.

    Only what APPEARED on the screen is judged: pixels that differ and are ink (not background) in `second`. A move explains
    them (the element is now there); a deletion leaves nothing that appeared, so it can never be mistaken for a move, and
    unchanged text or borders next to the element do not count against a shift.
    """
    height, width = first.shape[:2]
    strong = max(tolerance * 3, 30)          # a moved element is a strong change; JPEG ringing and text smoothing are weak ones
    changed = _different(first, second, strong)
    appeared = changed & (numpy.abs(second - _background(second)).max(axis=2) > strong)
    total = int(appeared.sum())
    if total == 0:
        return (0, 0, 0.0, 0.0)
    best, scores = (0, 0, 0.0), []
    for dy in range(-MAX_SHIFT, MAX_SHIFT + 1):
        for dx in range(-MAX_SHIFT, MAX_SHIFT + 1):
            if dx == 0 and dy == 0:
                continue
            a = first[max(0, -dy):height - max(0, dy), max(0, -dx):width - max(0, dx)]
            b = second[max(0, dy):height - max(0, -dy), max(0, dx):width - max(0, -dx)]
            if a.size == 0 or a.shape != b.shape:
                continue
            window = appeared[max(0, dy):height - max(0, -dy), max(0, dx):width - max(0, -dx)]
            explained = float((window & ~_different(a, b, strong)).sum()) / total
            scores.append(explained)
            if explained > best[2]:
                best = (dx, dy, explained)
    return best + (float(numpy.mean(scores)) if scores else 0.0,)


def _extension(first, second, local: tuple, tolerance: int):
    """
    A strip that is background in one image and ink in the other, and that continues an element on one side, is that element
    growing or shrinking. Returns the description, or None when the strip stands alone (something added or removed).
    """
    left, top, width, height = local
    bg_first, bg_second = _background(first), _background(second)
    inside_first = first[top:top + height, left:left + width]
    inside_second = second[top:top + height, left:left + width]
    ink_first = float((numpy.abs(inside_first - bg_first).max(axis=2) > tolerance).mean())
    ink_second = float((numpy.abs(inside_second - bg_second).max(axis=2) > tolerance).mean())
    if ink_first < 0.15 and ink_second > 0.6:
        grew, source, bg = True, first, bg_first
    elif ink_second < 0.15 and ink_first > 0.6:
        grew, source, bg = False, second, bg_second
    else:
        return None
    band = 3
    neighbours = {
        "left": source[top:top + height, max(left - band, 0):left],
        "right": source[top:top + height, left + width:left + width + band],
        "above": source[max(top - band, 0):top, left:left + width],
        "below": source[top + height:top + height + band, left:left + width],
    }
    touching = [side for side, pixels in neighbours.items()
                if pixels.size and float((numpy.abs(pixels - bg).max(axis=2) > tolerance).mean()) > 0.5]
    if not touching:
        return None
    sign = "+" if grew else "-"
    if touching[0] in ("left", "right"):
        return f"width {sign}{width} px (the element {'grew' if grew else 'shrank'} on the {'right' if touching[0] == 'left' else 'left'})"
    return f"height {sign}{height} px (the element {'grew' if grew else 'shrank'} {'downwards' if touching[0] == 'above' else 'upwards'})"


def _ink_colour(crop, tolerance: int):
    """The colour of the element itself (the median of everything that is not the background), or None."""
    ink = numpy.abs(crop - _background(crop)).max(axis=2) > tolerance
    return numpy.median(crop[ink], axis=0) if ink.any() else None


def _colour_note(first, second, tolerance: int) -> str:
    """"; the colour also changed #e77817 -> #c23029" when the element is in another colour as well."""
    colour_a, colour_b = _ink_colour(first, tolerance), _ink_colour(second, tolerance)
    if colour_a is None or colour_b is None or float(numpy.abs(colour_a - colour_b).max()) <= tolerance * 2:
        return ""
    return f"; the colour also changed {_hex(colour_a)} -> {_hex(colour_b)}"


def _direction(dx: int, dy: int) -> str:
    parts = []
    if dx:
        parts.append(f"{abs(dx)} px {'right' if dx > 0 else 'left'}")
    if dy:
        parts.append(f"{abs(dy)} px {'down' if dy > 0 else 'up'}")
    return " and ".join(parts)


def classify(baseline, actual, region: dict, tolerance: int = 10, lossy: bool = False) -> dict:
    """{"kind", "detail"} for one differing area; both images are RGB arrays of the same size."""
    first, (crop_left, crop_top) = _crop(baseline, region)
    second, _ = _crop(actual, region)
    if first.shape != second.shape or first.size == 0:
        return {"kind": "content", "detail": "the area is outside one of the images"}
    if region["width"] * region["height"] > MAX_SEARCH_PIXELS:
        return {"kind": "content", "detail": "a large area changed (a picture or a block of content)"}

    grown = _extension(first, second, (region["x"] - crop_left, region["y"] - crop_top, region["width"], region["height"]), tolerance)
    if grown:
        return {"kind": "size", "detail": grown + _colour_note(first, second, tolerance)}

    dx, dy, explained, average = _shift_match(first, second, tolerance)
    if (dx or dy) and explained >= MIN_MATCH and explained >= PEAK_OVER_AVERAGE * max(average, 0.02):
        return {"kind": "position", "detail": f"moved {_direction(dx, dy)} in the screen compared with the reference"
                + _colour_note(first, second, tolerance)}

    box_a, box_b = _ink_box(first, tolerance), _ink_box(second, tolerance)
    if box_a and not box_b:
        return {"kind": "content", "detail": "present in the reference but missing on the screen"}
    if box_b and not box_a:
        return {"kind": "content", "detail": "present on the screen but not in the reference"}
    if box_a and box_b and (abs(box_a[2] - box_b[2]) > 3 or abs(box_a[3] - box_b[3]) > 3):
        pieces = []
        if abs(box_a[2] - box_b[2]) > 3:
            pieces.append(f"width {box_a[2]} -> {box_b[2]} px")
        if abs(box_a[3] - box_b[3]) > 3:
            pieces.append(f"height {box_a[3]} -> {box_b[3]} px")
        return {"kind": "size", "detail": ", ".join(pieces) + " (reference -> screen)" + _colour_note(first, second, tolerance)}

    edges_a, edges_b = _edges(first), _edges(second)
    norm = float(numpy.sqrt((edges_a ** 2).sum()) * numpy.sqrt((edges_b ** 2).sum()))
    similarity = float((edges_a * edges_b).sum() / norm) if norm > 0 else 1.0
    changed = _different(first, second, tolerance)
    if similarity >= 0.8 and changed.any():
        color_a = numpy.median(first[changed], axis=0)
        color_b = numpy.median(second[changed], axis=0)
        if lossy and float(numpy.abs(color_a - color_b).max()) < LOSSY_COLOUR_NOISE:
            return {"kind": "noise", "detail": "JPEG compression of the design"}
        return {"kind": "colour", "detail": f"{_hex(color_a)} -> {_hex(color_b)} (reference -> screen), same shape"}
    return {"kind": "content", "detail": "text, an icon or a picture is different"}


def describe(baseline_image: Image.Image, actual_image: Image.Image, regions: list, tolerance: int = 10, lossy: bool = False) -> list:
    """Adds "kind" and "detail" to the largest differing areas (the rest keep none) and returns the list.
    lossy = the reference is a JPEG: areas that differ only by compression noise are removed from the list."""
    if baseline_image.size != actual_image.size:
        return regions
    baseline = numpy.asarray(baseline_image.convert("RGB"))
    actual = numpy.asarray(actual_image.convert("RGB"))
    for region in regions[:MAX_CLASSIFIED]:
        try:
            region.update(classify(baseline, actual, region, tolerance, lossy))
        except Exception as error:                           # a description is a help, never a reason to fail a comparison
            region.update({"kind": "content", "detail": f"could not be described ({error})"})
    regions[:] = [region for region in regions if region.get("kind") != "noise"]
    return regions


def summary(regions: list, limit: int = 4) -> str:
    """One line for a table cell: 'colour at (992, 744): #C23029 -> #E77817; position at (10, 20): moved 8 px right'."""
    lines = [f"{region['kind']} at ({region['x']}, {region['y']}): {region['detail']}" for region in regions if region.get("kind")]
    more = f"; and {len(lines) - limit} more" if len(lines) > limit else ""
    return "; ".join(lines[:limit]) + more
