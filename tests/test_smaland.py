from smaland import Smaland, constants
import os
import pytest
import datetime

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
    accnout_id = data['accounts'][-1]['accountId']


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

    # Get watchlists
    instrument_id = 742358
    res = sl.get_watchlist()
    assert res.status_code < 300
    data = res.json()
    assert data != None

    # Add to watchlist
    res = sl.add_to_watchlist(
        instrument_id=instrument_id, watchlist_id=data[0]["id"])
    assert res.status_code < 300

    # Was it added?
    res = sl.get_watchlist()
    data_t = res.json()
    assert res.status_code < 300
    assert data_t != None
    assert str(instrument_id) in data_t[0]['orderbooks']

    # Delete from watchlist
    res = sl.delete_from_watchlist(
        instrument_id=instrument_id, watchlist_id=data[0]["id"])
    assert res.status_code < 300

    # Was it deleted?
    res = sl.get_watchlist()
    data_t = res.json()
    assert res.status_code < 300
    assert data_t != None
    assert str(instrument_id) not in data_t[0]['orderbooks']


def test_get_instrument():
    instrument_id = 742358

    res = sl.get_instrument(constants["public"]["STOCK"], instrument_id)
    assert res.status_code < 300
    data = res.json()

    assert len(data.keys()) > 0


def test_get_orderbook():

    instrument_id = 742358
    res = sl.get_orderbook(constants["public"]["STOCK"], instrument_id)
    assert res.status_code < 300
    data = res.json()

    assert len(data.keys()) > 0


def test_get_chartdata():

    instrument_id = 742358
    res = sl.get_chartdata(instrument_id)
    assert res.status_code < 300
    data = res.json()
    assert len(data.keys()) > 0


def test_place_get_delete_order():
    global accnout_id
    instrument_id = 5330
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

    options = {
        "accountId": accnout_id,
        "orderbookId": instrument_id,
        "orderType": 'BUY',
        "price": sl.get_orderbook(instrument_type=constants['public']['STOCK'], orderbook_id=instrument_id).json()['orderbook']['lastPrice'],
        "validUntil": tomorrow.strftime("%Y-%m-%d"),
        "volume": 1
    }

    # Place order
    res_p = sl.place_order(options=options)
    assert res_p.status_code < 300

    # Get order
    res_g = sl.get_order(sl._constants['public']['STOCK'],
                         account_id=accnout_id, order_id=res_p.json()['orderId'])
    assert res_g.status_code < 300

    # Delete order
    res_d = sl.delete_order(account_id=accnout_id,
                            order_id=res_p.json()['orderId'])
    assert res_d.status_code < 300

    #Get order again, should fail if deleted correctly 
    res_g_2 = sl.get_order(
        sl._constants['public']['STOCK'], account_id=accnout_id, order_id=res_p.json()['orderId'])
    assert res_g_2.status_code == 404
    print("BE CAREFUL, IF THIS TEST FAILED AN ORDER MAY HAVE BEEN PLACED. PLEAS LOG INTO YOUR AVANZA ACCOUNT AND DELETE THE ORDER")


def test_search():

    res = sl.search("avanza")
    assert res.status_code < 300
    assert len(res.json()["hits"]) > 0
 


def test_get_df_all_stocks():

    df = sl.get_df_all_stocks()
    assert df.shape[0] > 100
    assert df.shape[1] > 5