from smaland import Smaland
import os
import pytest

sl = Smaland()
accnout_id = None


def test_credentials():
    credentials = {
        "username": os.getenv("username_av"),
        "password": os.getenv("password_av"),
        "secret": os.getenv("secret_av")
    }

    assert credentials["username"] != None
    assert credentials["password"] != None
    assert credentials["secret"] != None


def test_authentication():
    credentials = {
        "username": os.getenv("username_av"),
        "password": os.getenv("password_av"),
        "secret": os.getenv("secret_av")
    }

    res = sl.authenticate(credentials)
    assert res.status_code < 300


def test_overview():
    global accnout_id
    res = sl.get_overview()
    assert res.status_code < 300

    data = res.json()
    assert len(data.keys()) > 0
    accnout_id = data['accounts'][0]['accountId']


def test_account_overview():
    global accnout_id
    res = sl.get_account_overview(accnout_id)
    assert res.status_code < 300

    data = res.json()
    assert len(data.keys()) > 0


def test_get_positions():
    res = sl.get_positions()
    assert res.status_code < 300


def test_get_deals_and_orders():
    res = sl.get_deals_and_orders()
    assert res.status_code < 300


def test_get_transactions():
    global accnout_id
    options = {
        "from": "2000-01-01",
        "to": "2020-01-27",
        "maxAmount": 100000,
        "minAmount": 0,
    }

    res = sl.get_transactions(accnout_id, options)
    assert res.status_code < 300



def test_watchlist():

    #Get watchlists
    instrument_id = 742358
    res = sl.get_watchlist()
    assert res.status_code < 300
    data = res.json()
    assert data != None

    #Add to watchlist
    res = sl.add_to_watchlist(instrument_id = instrument_id, watchlist_id = data[0]["id"])
    assert res.status_code < 300

    #Was it added?
    res = sl.get_watchlist()
    data_t = res.json()
    assert res.status_code < 300
    assert data_t != None
    assert str(instrument_id) in data_t[0]['orderbooks']

    #Delete from watchlist
    res = sl.delete_from_watchlist(instrument_id = instrument_id, watchlist_id = data[0]["id"])
    assert res.status_code < 300

    #Was it deleted?
    res = sl.get_watchlist()
    data_t = res.json()
    assert res.status_code < 300
    assert data_t != None
    assert str(instrument_id) not in data_t[0]['orderbooks']


