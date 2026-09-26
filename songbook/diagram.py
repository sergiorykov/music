"""Render a guitar Voicing as a compact inline SVG chord diagram.

Colours come from CSS: lines and dots use currentColor, finger numbers use
the .dg-finger class, so one SVG works in the dark site theme and in print.
"""

from __future__ import annotations

from .voicings import Voicing

STRINGS = 6
PAD_LEFT = 16      # room for the base-fret number
PAD_RIGHT = 6
PAD_TOP = 14       # room for open / muted markers
PAD_BOTTOM = 4
STRING_GAP = 11
FRET_GAP = 13
DOT_R = 4.6


def _x(string: int) -> float:
    return PAD_LEFT + string * STRING_GAP


def _y(fret_row: int) -> float:
    """Vertical centre of a fret row (1-based)."""
    return PAD_TOP + (fret_row - 0.5) * FRET_GAP


def render(v: Voicing) -> str:
    rows = max(4, max(v.frets))
    width = PAD_LEFT + (STRINGS - 1) * STRING_GAP + PAD_RIGHT
    height = PAD_TOP + rows * FRET_GAP + PAD_BOTTOM
    grid_bottom = PAD_TOP + rows * FRET_GAP
    out: list[str] = [
        f'<svg class="dg" viewBox="0 0 {width} {height}" width="{width}" height="{height}"'
        f' xmlns="http://www.w3.org/2000/svg" role="img">'
    ]

    # Frets and strings
    for r in range(rows + 1):
        y = PAD_TOP + r * FRET_GAP
        out.append(f'<line class="dg-line" x1="{_x(0)}" y1="{y}" x2="{_x(STRINGS - 1)}" y2="{y}" stroke="currentColor" stroke-width="0.8"/>')
    for s in range(STRINGS):
        out.append(f'<line class="dg-line" x1="{_x(s)}" y1="{PAD_TOP}" x2="{_x(s)}" y2="{grid_bottom}" stroke="currentColor" stroke-width="0.8"/>')

    # Nut or base-fret number
    if v.base_fret == 1:
        out.append(f'<line class="dg-line" x1="{_x(0) - 0.5}" y1="{PAD_TOP}" x2="{_x(STRINGS - 1) + 0.5}" y2="{PAD_TOP}" stroke="currentColor" stroke-width="3"/>')
    else:
        out.append(
            f'<text class="dg-fret" x="{PAD_LEFT - 5}" y="{_y(1) + 3}" text-anchor="end"'
            f' font-size="9" fill="currentColor">{v.base_fret}</text>'
        )

    # Open / muted markers
    for s, fret in enumerate(v.frets):
        x, y = _x(s), PAD_TOP - 6
        if fret == 0:
            out.append(f'<circle class="dg-line" cx="{x}" cy="{y}" r="2.8" fill="none" stroke="currentColor" stroke-width="0.9"/>')
        elif fret < 0:
            d = 2.5
            out.append(
                f'<path class="dg-line" d="M{x - d} {y - d}L{x + d} {y + d}M{x + d} {y - d}L{x - d} {y + d}"'
                f' stroke="currentColor" stroke-width="0.9"/>'
            )

    # Barres
    for b in v.barres:
        strings = [s for s, f in enumerate(v.frets) if f == b]
        if len(strings) < 2:
            continue
        x1, x2, y = _x(min(strings)), _x(max(strings)), _y(b)
        out.append(
            f'<rect class="dg-dot" x="{x1 - DOT_R}" y="{y - DOT_R}" width="{x2 - x1 + 2 * DOT_R}"'
            f' height="{2 * DOT_R}" rx="{DOT_R}" fill="currentColor"/>'
        )

    # Finger dots
    for s, fret in enumerate(v.frets):
        if fret <= 0:
            continue
        x, y = _x(s), _y(fret)
        out.append(f'<circle class="dg-dot" cx="{x}" cy="{y}" r="{DOT_R}" fill="currentColor"/>')
        finger = v.fingers[s] if v.fingers else 0
        if finger:
            out.append(
                f'<text class="dg-finger" x="{x}" y="{y + 2.4}" text-anchor="middle"'
                f' font-size="6.5" font-weight="bold" fill="#fff">{finger}</text>'
            )

    out.append("</svg>")
    return "".join(out)
