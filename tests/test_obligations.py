from datetime import date, timedelta

import pytest
from dateutil.relativedelta import relativedelta
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope='session')


def _create_payload(**overrides) -> dict:
    payload = {
        'title': 'Яндекс.Плюс',
        'amount': 299.00,
        'currency': 'RUB',
        'category': 'subscription',
        'recurrence': 'monthly',
        'next_payment_date': str(date.today() + timedelta(days=5)),
    }
    payload.update(overrides)
    return payload


# ── POST /obligations ────────────────────────────────────────────────


async def test_create_obligation_returns_201(client: AsyncClient):
    resp = await client.post('/obligations', json=_create_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body['obligation']['status'] == 'active'
    assert body['warning'] is None


async def test_create_obligation_expired_if_past_date(client: AsyncClient):
    past = str(date.today() - timedelta(days=10))
    resp = await client.post('/obligations', json=_create_payload(
        next_payment_date=past, recurrence=None, category='bill',
    ))
    assert resp.status_code == 201
    assert resp.json()['obligation']['status'] == 'expired'


async def test_create_duplicate_returns_warning(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(title='Netflix'))
    resp = await client.post('/obligations', json=_create_payload(title='Netflix'))
    body = resp.json()
    assert body['warning'] == 'Активное обязательство с таким названием уже существует'
    assert body['obligation']['status'] == 'active'


async def test_create_duplicate_case_insensitive(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(title='Netflix'))
    resp = await client.post('/obligations', json=_create_payload(title='netflix'))
    assert resp.json()['warning'] is not None


async def test_no_warning_if_previous_expired(client: AsyncClient):
    past = str(date.today() - timedelta(days=10))
    await client.post('/obligations', json=_create_payload(
        next_payment_date=past, recurrence=None, category='bill',
    ))
    resp = await client.post('/obligations', json=_create_payload())
    assert resp.json()['warning'] is None


# ── GET /obligations ─────────────────────────────────────────────────


async def test_list_obligations(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(title='A'))
    await client.post('/obligations', json=_create_payload(title='B'))
    resp = await client.get('/obligations')
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_filter_by_category(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(category='subscription'))
    await client.post('/obligations', json=_create_payload(
        title='Tax', category='bill', recurrence=None,
    ))
    resp = await client.get('/obligations?category=subscription')
    assert len(resp.json()) == 1


async def test_list_filter_by_status(client: AsyncClient):
    await client.post('/obligations', json=_create_payload())
    past = str(date.today() - timedelta(days=1))
    await client.post('/obligations', json=_create_payload(
        title='Old', recurrence=None, category='bill', next_payment_date=past,
    ))
    resp = await client.get('/obligations?status=expired')
    assert len(resp.json()) == 1


# ── Lazy expiry ──────────────────────────────────────────────────────


async def test_lazy_expire_one_time(client: AsyncClient):
    past = str(date.today() - timedelta(days=1))
    await client.post('/obligations', json=_create_payload(
        title='OneTime', recurrence=None, next_payment_date=past,
    ))
    await client.post('/obligations', json=_create_payload(title='Active'))

    resp = await client.get('/obligations?status=active')
    titles = [o['title'] for o in resp.json()]
    assert 'Active' in titles
    assert 'OneTime' not in titles


async def test_lazy_expire_recurring_stays_active(client: AsyncClient):
    past = str(date.today() - timedelta(days=10))
    await client.post('/obligations', json=_create_payload(
        title='Sub', recurrence='monthly', next_payment_date=past,
    ))
    resp = await client.get('/obligations?status=active')
    assert len(resp.json()) == 1
    assert resp.json()[0]['title'] == 'Sub'


# ── GET /obligations/upcoming ────────────────────────────────────────


async def test_upcoming_basic(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(
        next_payment_date=str(date.today() + timedelta(days=3)),
    ))
    await client.post('/obligations', json=_create_payload(
        title='Far',
        next_payment_date=str(date.today() + timedelta(days=30)),
    ))
    resp = await client.get('/obligations/upcoming?days=7')
    body = resp.json()
    assert len(body['obligations']) == 1
    assert body['obligations'][0]['title'] == 'Яндекс.Плюс'


async def test_upcoming_totals(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(
        amount=100.50, next_payment_date=str(date.today() + timedelta(days=1)),
    ))
    await client.post('/obligations', json=_create_payload(
        title='USD sub', amount=9.99, currency='USD',
        next_payment_date=str(date.today() + timedelta(days=2)),
    ))
    resp = await client.get('/obligations/upcoming?days=7')
    totals = resp.json()['totals']
    assert float(totals['RUB']) == 100.50
    assert float(totals['USD']) == 9.99


async def test_upcoming_renewal_alerts(client: AsyncClient):
    await client.post('/obligations', json=_create_payload(
        next_payment_date=str(date.today() + timedelta(days=3)),
    ))
    await client.post('/obligations', json=_create_payload(
        title='OneTime bill', category='bill', recurrence=None,
        next_payment_date=str(date.today() + timedelta(days=1)),
    ))
    resp = await client.get('/obligations/upcoming?days=7')
    alerts = resp.json()['renewal_alerts']
    assert len(alerts) == 1
    assert alerts[0]['title'] == 'Яндекс.Плюс'


# ── POST /obligations/{id}/pay ───────────────────────────────────────


async def _create_id(client: AsyncClient, **kw) -> str:
    r = await client.post('/obligations', json=_create_payload(**kw))
    return r.json()['obligation']['id']


async def test_pay_monthly(client: AsyncClient):
    future = str(date.today() + timedelta(days=15))
    oid = await _create_id(client, next_payment_date=future)
    resp = await client.post(f'/obligations/{oid}/pay')
    assert resp.status_code == 200
    body = resp.json()
    assert body['obligation']['status'] == 'active'
    assert body['obligation']['next_payment_date'] != future
    assert body['payment']['amount'] == '299.00'


async def test_pay_quarterly(client: AsyncClient):
    oid = await _create_id(client, recurrence='quarterly')
    resp = await client.post(f'/obligations/{oid}/pay')
    ob = resp.json()['obligation']
    assert ob['status'] == 'active'
    expected = date.today() + timedelta(days=5) + relativedelta(months=3)
    assert ob['next_payment_date'] == str(expected)


async def test_pay_yearly(client: AsyncClient):
    oid = await _create_id(client, recurrence='yearly')
    resp = await client.post(f'/obligations/{oid}/pay')
    ob = resp.json()['obligation']
    assert ob['status'] == 'active'
    expected = date.today() + timedelta(days=5) + relativedelta(years=1)
    assert ob['next_payment_date'] == str(expected)


async def test_pay_one_time_becomes_cancelled(client: AsyncClient):
    oid = await _create_id(client, recurrence=None, category='bill')
    resp = await client.post(f'/obligations/{oid}/pay')
    assert resp.json()['obligation']['status'] == 'cancelled'


async def test_pay_31st_monthly_boundary(client: AsyncClient):
    jan31 = date(date.today().year, 1, 31)
    if jan31 < date.today():
        jan31 = date(date.today().year + 1, 1, 31)
    oid = await _create_id(client, next_payment_date=str(jan31))
    resp = await client.post(f'/obligations/{oid}/pay')
    new_date = resp.json()['obligation']['next_payment_date']
    d = date.fromisoformat(new_date)
    assert d.month == 2
    assert d.day in (28, 29)


# ── Pay/cancel non-active ────────────────────────────────────────────


async def test_pay_expired_returns_422(client: AsyncClient):
    past = str(date.today() - timedelta(days=1))
    oid = await _create_id(client, recurrence=None, next_payment_date=past)
    resp = await client.post(f'/obligations/{oid}/pay')
    assert resp.status_code == 422


async def test_cancel_expired_returns_422(client: AsyncClient):
    past = str(date.today() - timedelta(days=1))
    oid = await _create_id(client, recurrence=None, next_payment_date=past)
    resp = await client.patch(f'/obligations/{oid}/cancel')
    assert resp.status_code == 422


async def test_cancel_active(client: AsyncClient):
    oid = await _create_id(client)
    resp = await client.patch(f'/obligations/{oid}/cancel')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'cancelled'


async def test_cancel_already_cancelled_returns_422(client: AsyncClient):
    oid = await _create_id(client)
    await client.patch(f'/obligations/{oid}/cancel')
    resp = await client.patch(f'/obligations/{oid}/cancel')
    assert resp.status_code == 422


# ── DELETE /obligations/{id} ─────────────────────────────────────────


async def test_delete_returns_204(client: AsyncClient):
    oid = await _create_id(client)
    resp = await client.delete(f'/obligations/{oid}')
    assert resp.status_code == 204

    resp = await client.get('/obligations')
    assert len(resp.json()) == 0


async def test_delete_nonexistent_returns_404(client: AsyncClient):
    from uuid import uuid4
    resp = await client.delete(f'/obligations/{uuid4()}')
    assert resp.status_code == 404


# ── SSE broadcast ────────────────────────────────────────────────────


async def test_delete_sends_sse_broadcast(client: AsyncClient):
    import asyncio

    from app.core.sse import _clients

    queue: asyncio.Queue = asyncio.Queue()
    _clients.append(queue)
    try:
        oid = await _create_id(client)
        await client.delete(f'/obligations/{oid}')

        assert not queue.empty()
        event = queue.get_nowait()
        assert event['event'] == 'obligation_deleted'
        assert oid in event['data']
    finally:
        _clients.remove(queue)
