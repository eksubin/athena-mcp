from app.services.world import allocate_plot, structure_position, structure_type_for_status


def test_allocate_plot_no_collisions():
    seen = set()
    for n in range(300):
        coords = allocate_plot(n)
        assert coords not in seen
        seen.add(coords)


def test_allocate_plot_origin():
    assert allocate_plot(0) == (0, 0)


def test_structure_type_mapping():
    assert structure_type_for_status("applied") == "tree"
    assert structure_type_for_status("offer") == "landmark"
    assert structure_type_for_status("rejected") == "stump"


def test_structure_position_packs_within_plot_without_overlap():
    positions = {structure_position((0, 0), i) for i in range(20)}
    assert len(positions) == 20
