
from .constants import constants
import requests as r
import json
from .totp import totp
import websocket
import re
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import pandas as pd
import time
try:
    import thread
except ImportError:
    import _thread as thread
import time
import threading


BASE_URL = 'https://www.avanza.se'
MIN_INACTIVE_MINUTES = 30
MAX_INACTIVE_MINUTES = 60 * 24
SOCKET_URL = 'wss://www.avanza.se/_push/cometd'
MAX_BACKOFF_MS = 2 * 60 * 1000

HEADERS = {
    'content-type': 'application/json',
    'accept': '*/*',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0',
}


def base_request(url, method='GET', data={}, headers={}):

    headers.update(HEADERS)
    data = json.dumps(data)
    headers['content-length'] = str(len(data))
    resp = r.request(method=method,
                     url=BASE_URL + url,
                     data=data,
                     headers=headers)

    return resp


class Smaland():
    def __init__(self):
        self._authenticated = False
        self._credentials = None
        self._security_token = None
        self._authentication_session = None
        self._push_subscription_id = None
        self._customer_id = None
        self._constants = constants
        self._client_id = None

        # socket
        self._subscriptions = {}
        self._socket = None
        self._socket_message_count = 0

    def _send(self, ws, json_object):
        self._socket_message_count = self._socket_message_count + 1
        socket_message_count = self._socket_message_count
        json_object[0]["id"] = socket_message_count
        ws.send(json.dumps(json_object))

    def _init_socket(self):

        def _on_message(ws, message):
            message = json.loads(message)

            if(message[0]["channel"] == '/meta/disconnect'):
                pass

            elif(message[0]["channel"] == "/meta/handshake"):
                self._client_id = message[0]["clientId"]
                send_obj = [{"channel": "/meta/connect",
                             "connectionType": "websocket",
                             "advice": {"timeout": 0},
                             "clientId": message[0]["clientId"]}]

                self._send(ws, send_obj)

            elif(message[0]["channel"] == '/meta/connect'):
                send_obj = [{"channel": "/meta/connect",
                             "clientId": self._client_id,
                             "connectionType": 'websocket'
                             }]

                self._send(ws, send_obj)

            elif(message[0]["channel"] == "/meta/subscribe"):
                self._subscriptions[message[0]["subscription"]
                                    ]["successful"] = message[0]["successful"]

            elif(message[0]["channel"] in self._subscriptions.keys()):
                if(self._subscriptions[message[0]["channel"]]["successful"]):

                    # If is_class, call _callback, else call function
                    if(self._subscriptions[message[0]["channel"]]['is_class']):
                        self._subscriptions[message[0]["channel"]]["callback"]._callback(
                            message[0]["data"])
                    else:
                        self._subscriptions[message[0]["channel"]]["callback"](
                            message[0]["data"])

        def _on_error(ws, error):
            print(error)

        def _on_close(ws):
            print("Socket Closed")

        def _on_open(ws):

            def run(*args):

                auth_message = [{"advice": {"timeout": 60000, "interval": 0},
                                 "channel": "/meta/handshake",
                                            "ext": {"subscriptionId":  self._push_subscription_id},
                                            "minimumVersion": "1.0",
                                            "supportedConnectionTypes": ["websocket", "long-polling", "callback-polling"],
                                            "version": "1.0"}]
                self._send(ws, auth_message)

            thread.start_new_thread(run, ())

        websocket.enableTrace(False)
        self._socket = websocket.WebSocketApp(SOCKET_URL,
                                              on_message=_on_message,
                                              on_error=_on_error,
                                              on_close=_on_close,
                                              on_open=_on_open)

    def run_forever(self, ws):
        threading.Thread(target=ws.run_forever).start()

    def subscribe(self, subscription_string, callback):
        """
        Subscribes to real-time data through websockets. 


        Parameters
        ----------
        subscription_string : string on format {channel}/{orderbook_id}
            channel is the type if rt-data: 
                constants["public"]["ACCOUNTS"]
                constants["public"]["QUOTES"] 
                constants["public"]["ORDERDEPTHS"]
                constants["public"]["TRADES"]
                constants["public"]["BROKERTRADESUMMARY"]
                constants["public"]["POSITIONS"] 
                constants["public"]["ORDERS"] 
                constants["public"]["DEALS"] 

        callback : function OR class that implements SubscriptionCallback
            function:
                def _callback(message):
                    print(message)

            class: 
                class SubscriptionCallback:
                    def __init__(self):
                        self._context = {}

                    def _callback(self, message):
                        print(message)
        """

        if(self._push_subscription_id == None):
            raise Exception("No subscription string")

        re_connect_soc = False
        if(self._socket == None):
            re_connect_soc = True
        elif(self._socket.sock == None):
            re_connect_soc = True

        if(re_connect_soc):
            self._init_socket()
            self.run_forever(self._socket)
            time.sleep(2)

        if(subscription_string in self._subscriptions.keys()):
            raise Exception(
                "Already subsrcibed the channel {subscription_string}")

        self._subscriptions[subscription_string] = {
            "callback": callback,
            "successful": False,
            "is_class": type(callback) == type
        }

        sub_obj = [{
            "channel": "/meta/subscribe",
            "clientId": self._client_id,
            "subscription": subscription_string
        }]

        self._send(self._socket, sub_obj)

    def close_all_subscriptions(self):
        self._subscriptions = {}
        self._socket.close()

    def _schedule_reauth(self, authentication_timeout=60*60):
        pass

    def authenticate(self, credentials):
        self._credentials = credentials

        # Authentication data
        try:
            data = {
                "maxInactiveMinutes": MAX_INACTIVE_MINUTES,
                "password": credentials.get("password"),
                "username": credentials.get("username"),
            }
        except Exception as e:
            print(e)
            print("Invalid credentials, needs password, username, and XXX")

        res = base_request(
            self._constants["paths"]["AUTHENTICATION_PATH"], method='POST', data=data)

        res_data = res.json()
        if(res.status_code >= 300):
            return res

        # Tow 2FA
        if(res_data.get("twoFactorLogin", False) == False):
            return res_data, 200

        tfaOpts = res_data["twoFactorLogin"]

        if(tfaOpts["method"] != 'TOTP'):
            return {"message": "Unsuported 2FA method"}, 400

        # Secret for 2FA
        secret = credentials.get("secret")
        totpCode = totp(secret)

        data_2fa = {
            "method": 'TOTP',
            "totpCode": totpCode
        }

        headers_2fa = dict()
        headers_2fa['Cookie'] = 'AZAMFATRANSACTION={}'.format(
            tfaOpts['transactionId'])

        res_sec = base_request(
            self._constants["paths"]["TOTP_PATH"], method='POST', data=data_2fa, headers=headers_2fa)

        # Failed authentication
        if(res_sec.status_code >= 300):
            print("Failed authentication")
            return res_sec

        res_sec_data = res_sec.json()
        self._authenticated = True
        self._credentials = credentials
        self._security_token = res_sec.headers['x-securitytoken']
        self._authentication_session = res_sec_data['authenticationSession']
        self._push_subscription_id = res_sec_data['pushSubscriptionId']
        self._customer_id = res_sec_data['customerId']

        # TODO
        # self._schedule_reauth(60*60)

        print("successful authentication")
        return res_sec

    def get_overview(self):
        """Returns an overview of all accounts

        Returns:
        dict:account_overview
        """
        return self.call(self._constants["paths"]["OVERVIEW_PATH"], method='GET')

    def get_account_overview(self, account_id):
        url = self._constants["paths"]["ACCOUNT_OVERVIEW_PATH"].replace(
            '{0}', account_id)
        return self.call(url, method='GET')

    def get_positions(self):
        return self.call(self._constants["paths"]["POSITIONS_PATH"], method='GET')

    def get_deals_and_orders(self):
        return self.call(self._constants["paths"]["DEALS_AND_ORDERS_PATH"], method='GET')

    def get_transactions(self, account_or_transaction_type, options):
        """
        Get all transactions of an account.

        Parameters
        ----------
        account_or_transaction_type : string, a account_id or {transaction_type}
        options: dict
            options = {
                "from"          : {string} On the form YYYY-MM-DD,
                "to"            : {string} On the form YYYY-MM-DD,
                "maxAmount"     : {int} Only fetch transactions of at most this value,
                "minAmount"     : {int} Only fetch transactions of at least this value,
                "orderbookId"   : {string|list} Only fetch transactions involving this/these orderbooks
            }

        -

        Returns
        --------


        """

        url = self._constants["paths"]["TRANSACTIONS_PATH"].replace(
            '{0}', str(account_or_transaction_type))

        if (type(options.get("orderbookId", None)) == list):
            options["orderbookId"] = ",".join(options["orderbookId"])

        options["includeInstrumentsWithNoOrderbook"] = 1

        query = urlencode(options)
        url_query = url + "?" + query

        return self.call(url_query, method='GET')

    def get_watchlist(self):
        return self.call(self._constants["paths"]["WATCHLISTS_PATH"], method='GET')

    def add_to_watchlist(self, instrument_id, watchlist_id):
        url = self._constants["paths"]["WATCHLISTS_ADD_DELETE_PATH"].replace(
            '{0}', str(watchlist_id)).replace('{1}', str(instrument_id))
        return self.call(url, method='PUT')

    def delete_from_watchlist(self, instrument_id, watchlist_id):
        url = self._constants["paths"]["WATCHLISTS_ADD_DELETE_PATH"].replace(
            '{0}', str(watchlist_id)).replace('{1}', str(instrument_id))
        return self.call(url, method='DELETE')

    def get_instrument(self, instrument_type, instrument_id):
        url = self._constants["paths"]["INSTRUMENT_PATH"].replace(
            '{0}', instrument_type.lower()).replace('{1}', str(instrument_id))
        return self.call(url, method='GET')

    def get_orderbook(self, instrument_type, orderbook_id):
        url = self._constants["paths"]["ORDERBOOK_PATH"].replace(
            '{0}', instrument_type.lower())
        url_query = url + "?orderbookId=" + str(orderbook_id)
        return self.call(url_query, method='GET')

    def get_orderbooks(self, orderbook_ids):
        url = self._constants["paths"]["ORDERBOOK_LIST_PATH"].replace(
            '{0}', ",".join([str(b) for b in orderbook_ids]))
        return self.call(url, method='GET')

    def get_chartdata(self, orderbook_id, period="three_years"):
        period = period.lower()
        url = self._constants["paths"]["CHARTDATA_PATH"].replace(
            '{0}', str(orderbook_id))
        url_query = url + "?" + urlencode({'timePeriod': period})
        return self.call(url_query, method='GET')

    def place_order(self, options):
        """
        @param options
            @param {str} accountId
            @param {str} oderbookId
            @param {str} orderType ("BUY" / "SELL")
            @param {int} price
            @param {str} validUntil a date "YYYY-MM-DD"
            @param {int} volume

        @return response object
            @params message, requestId, status, orderId
        """
        return self.call(self._constants["paths"]["ORDER_PLACE_DELETE_PATH"], method='POST', data=options)

    def get_order(self, instrument_type, account_id, order_id):
        """
        @param TODO
        """
        url = self._constants["paths"]["ORDER_GET_PATH"].replace(
            '{0}', instrument_type.lower())
        url_query = url + "?" + \
            urlencode({'accountId': str(account_id), 'orderId': str(order_id)})
        return self.call(url_query, method='GET')

    def edit_order(self, instrument_type, order_id, options):
        """
        @param instrument_type (str/int) Instrument type of the pertaining instrument. See [Instrument Types](#instrument-types).
        @param orderId (str/int) Order ID received when placing the order.

        @param options
            @param {str} accountId
            @param {str} oderbookId
            @param {str} orderType ("BUY" / "SELL")
            @param {int} price
            @param {str} validUntil a date "YYYY-MM-DD"
            @param {int} volume
            @param {orderCondition} NORMAL, FILL_OR_KILL, FILL_AND_KILL

        @return response object
            @params message, requestId, status, orderId
        """
        options['orderCondition'] = options.get('orderCondition', 'NORMAL')
        url = self._constants["paths"]["ORDER_EDIT_PATH"].replace(
            '{0}', instrument_type.lower()).replace('{1}', order_id)
        return self.call(url, method='PUT', data=options)

    def delete_order(self, account_id, order_id):
        url = self._constants["paths"]["ORDER_PLACE_DELETE_PATH"]
        url_query = url + "?" + \
            urlencode({'accountId': str(account_id), 'orderId': str(order_id)})
        return self.call(url_query, method='DELETE')

    def search(self, search_query, type=None):
        """
        Free text search for an instrument.

        @param {str} query Search query.
        @param {str} [type] An instrument type.
        """

        if(type):
            url = self._constants['paths']['SEARCH_PATH'].replace(
                '{0}', type.upper())
        else:
            url = self._constants['paths']['SEARCH_PATH'].replace('/{0}', '')

        query = urlencode(
            {
                "limit": 100,
                "query": search_query
            }
        )

        url_query = url + "?" + query
        return self.call(url_query, method='GET')

    def call(self, url, method='GET',  data={}):
        # Remove dangling question mark
        if (url[-1] == '?'):
            url = url[:-1]

        if(self._authenticated == False):
            raise Exception("Not authenticated")

        headers_auth = dict()
        headers_auth['X-AuthenticationSession'] = self._authentication_session
        headers_auth['X-SecurityToken'] = self._security_token

        res = base_request(url, method=method, data=data,
                           headers=headers_auth)

        return res

    def get_df_all_stocks(self):
        """
        Returns a pandas DataFrame of all Swedish stocks.
        NOTICE: This uses scraping methods, use with care!

        """

        url = BASE_URL + self._constants['paths']['LIST_ALL_SWEDISH_STOCKS']
        res = r.get(url)
        soup = BeautifulSoup(res.content, 'html.parser')
        res_parsed = soup.find_all('a', class_='ellipsis')

        def _parse_stock_list(row):
            url = str(row).split("\"")[3]
            name = str(row).split(">")[-2].split("<")[0].split("\r")[0]
            orderbook_id = url.split("/")[-2]

            return {
                "name": name,
                "orderbook_id": orderbook_id,
                "url": url
            }

        res_dict = []
        for row in res_parsed:
            res_dict.append(_parse_stock_list(row))

        df = pd.DataFrame(res_dict)

        res_parsed = soup.find_all('table', class_="u-standardTable")
        res_parsed_r = res_parsed[-2].find_all(
            'tr', class_=lambda value: value and value.startswith("row rowId"))

        def _str_to_float(inp_str):
            if(len(inp_str) == 0):
                return None
            else:
                return float(inp_str)

        def _parse_stock_list_more(row):
            output = dict()
            v = row.find_all('span')
            output['latest'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[0].text.strip().replace(",", ".")))
            output['pct_change_1d'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[1].text.strip().replace(",", ".")))
            output['pct_change_1y'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[2].text.strip().replace(",", ".")))
            output['market_cap'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[3].text.strip().replace(",", ".")))
            output['pe'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[4].text.strip().replace(",", ".")))
            output['pct_div'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[5].text.strip().replace(",", ".")))
            output['owners_avanza'] = _str_to_float(
                re.sub('[^z0-9+.*]+', '', v[6].text.strip().replace(",", ".")))
            output['list'] = v[7].text.strip()

            return output

        res_dict = []
        for row in res_parsed_r:
            res_dict.append(_parse_stock_list_more(row))

        return df.join(pd.DataFrame(res_dict))
