import math

PLOT_SPACING = 40  # world units between plot origins
STRUCTURE_SPACING = 4  # world units between structures inside one plot
STRUCTURES_PER_ROW = 6

STATUS_TO_STRUCTURE = {
    "saved": "sapling",
    "applied": "tree",
    "pending": "tree",
    "interview": "house",
    "offer": "landmark",
    "rejected": "stump",
}


def allocate_plot(n: int) -> tuple[int, int]:
    """The nth (0-indexed) signup's plot, filled outward ring by ring from
    the origin on a square lattice — see spec section 05.

    The caller starts at `count(world_plots)`, skips occupied positions
    (deleted accounts may leave gaps), and retries unique conflicts when
    concurrent signups choose the same position.
    """
    if n == 0:
        return (0, 0)
    ring = math.ceil((math.sqrt(n + 1) - 1) / 2)
    ring_start = (2 * ring - 1) ** 2
    side_len = 2 * ring
    offset = n - ring_start - 1
    side = offset // side_len
    pos = offset % side_len
    if side == 0:
        x, y = -ring + pos + 1, ring
    elif side == 1:
        x, y = ring, ring - pos - 1
    elif side == 2:
        x, y = ring - pos - 1, -ring
    else:
        x, y = -ring, -ring + pos + 1
    return (x * PLOT_SPACING, y * PLOT_SPACING)


def structure_position(plot_origin: tuple[int, int], structure_index: int) -> tuple[int, int]:
    """Pack structures left-to-right, top-to-bottom within a plot."""
    ox, oy = plot_origin
    row, col = divmod(structure_index, STRUCTURES_PER_ROW)
    return (ox + col * STRUCTURE_SPACING, oy - row * STRUCTURE_SPACING)


def structure_type_for_status(status: str) -> str:
    return STATUS_TO_STRUCTURE[status]
