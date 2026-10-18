from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from postgrest.exceptions import APIError

from app.api.deps import _ensure_profile_and_plot, _profile_row
from app.services.world import allocate_plot


class Client:
    def __init__(self, plots, race=False):
        self.plots = plots
        self.race = race

    def table(self, name):
        return Query(self, name)


class Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.filters = {}
        self.row = None
        self.single = False

    def select(self, *args, **kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def maybe_single(self):
        self.single = True
        return self

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        if self.table == 'profiles':
            return SimpleNamespace(data={'id': 'user'})
        if self.row:
            if self.client.race:
                self.client.race = False
                self.client.plots.append({**self.row, 'user_id': 'concurrent-user'})
                raise APIError({'code': '23505', 'message': 'coordinate collision'})
            self.client.plots.append(self.row)
            return SimpleNamespace(data=[self.row])
        rows = [p for p in self.client.plots if all(p[k] == v for k, v in self.filters.items())]
        if self.single and not rows:
            return None
        return SimpleNamespace(data=rows, count=len(rows))


def test_existing_profile_without_plot_is_repaired():
    client = Client([])
    _ensure_profile_and_plot('user', client)
    assert client.plots == [{'user_id': 'user', 'origin_x': 0, 'origin_y': 0}]
    _ensure_profile_and_plot('user', client)
    assert len(client.plots) == 1


def test_deleted_account_gap_does_not_reuse_occupied_plot():
    x, y = allocate_plot(1)
    client = Client([{'user_id': 'other', 'origin_x': x, 'origin_y': y}])
    _ensure_profile_and_plot('user', client)
    assert (client.plots[-1]['origin_x'], client.plots[-1]['origin_y']) == allocate_plot(2)


def test_coordinate_collision_is_retried_instead_of_ignored():
    client = Client([], race=True)
    _ensure_profile_and_plot('user', client)
    assert [p['user_id'] for p in client.plots] == ['concurrent-user', 'user']
    assert len({(p['origin_x'], p['origin_y']) for p in client.plots}) == 2


def test_new_session_clock_race_retries_read(monkeypatch):
    sleep = MagicMock()
    monkeypatch.setattr('app.api.deps.time.sleep', sleep)
    client = MagicMock()
    execute = client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    execute.side_effect = [APIError({'code': 'PGRST303', 'message': 'JWT issued at future'}), SimpleNamespace(data={'id': 'user'})]
    assert _profile_row('user', client) == {'id': 'user'}
    assert execute.call_count == 2
    sleep.assert_called_once_with(0.5)


@pytest.mark.parametrize('message,attempts', [('JWT expired', 1), ('JWT issued at future', 3)])
def test_session_retry_is_bounded_and_does_not_hide_other_errors(monkeypatch, message, attempts):
    monkeypatch.setattr('app.api.deps.time.sleep', MagicMock())
    client = MagicMock()
    execute = client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    execute.side_effect = APIError({'code': 'PGRST303', 'message': message})
    with pytest.raises(APIError):
        _profile_row('user', client)
    assert execute.call_count == attempts
