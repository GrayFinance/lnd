from cachetools import cached, LRUCache
from requests import request
from binascii import unhexlify
from base64 import b64encode
from json import loads, dumps

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Lnd:

    def __init__(self, url: str, macaroon: str, certificate: str) -> None:
        self.url = url
        self.macaroon = macaroon
        self.certificate = certificate
    
    def call(self, method: str, path: str, query=None, stream=False, data=None):
        headers = {"Grpc-Metadata-macaroon": self.macaroon}
        if (stream == False):
            return request(method=method, url=f"{self.url}{path}", params=query, headers=headers, verify=self.certificate, data=dumps(data)).json()
        else:
            return request(method=method, url=f"{self.url}{path}", params=query, headers=headers, verify=self.certificate, data=dumps(data), stream=True)
    
    def get_info(self) -> dict:
        return self.call("GET", "/v1/getinfo")
    
    def wallet_balance(self) -> dict:
        return self.call("GET", "/v1/balance/blockchain")
    
    def get_estimate_fee(self, address: str, amount: int, target_conf=144, spend_unconfirmed=True) -> dict:
        query = {"target_conf": target_conf, f"AddrToAmount[{address}]": amount, "spend_unconfirmed": spend_unconfirmed}
        return self.call("GET", "/v1/transactions/fee", query=query)

    def send_coins(self, address: str, amount: int, sat_per_vbyte: int = 1, spend_unconfirmed=True) -> dict:
        data = {"addr": address, "amount": amount, "sat_per_vbyte": sat_per_vbyte, "spend_unconfirmed": spend_unconfirmed}
        return self.call("POST", "/v1/transactions", data=data)
    
    def get_address(self, type_address="", account="") -> dict:
        query = {}
        if (type_address) and (account):
            query.update({"type": type_address, "account": account})
        return self.call("GET", "/v1/newaddress", query=query)

    def list_unspent(self, min_confs=1, max_confs=None, account=None) -> list:
        query = {"min_confs": min_confs, "max_confs": max_confs}
        if (max_confs == None):
            query["max_confs"] = self.get_info()["block_height"]
        
        if (account):
            query["account"] = account
        
        return self.call("GET", "/v1/utxos", query=query)
    
    def list_chain_txns(self, start_height=None, end_height=None, account=None) -> dict:
        query = {}
        if (start_height):
            query["start_height"] = start_height
        
        if (end_height):
            query["end_height"] = end_height
        
        if (account):
            query["account"] = account
        
        return self.call("GET", "/v1/transactions", query=query)
    
    def create_hold_invoice(self, payment_hash: str, amount: int, memo: str = "", expiry=(60 * 5)) -> dict:
        data = {"hash": b64encode(unhexlify(payment_hash)).decode(), "value": amount, "memo": memo, "expiry": expiry}
        return self.call("POST", "/v2/invoices/hodl", data=data)
    
    def cancel_invoice(self, payment_hash: str) -> dict:
        data = {"payment_hash": b64encode(unhexlify(payment_hash)).decode()}
        return self.call("POST", "/v2/invoices/cancel", data=data)
    
    def channels_balance(self) -> dict:
        return self.call("GET", "/v1/balance/channels")
    
    def transactions_subscribe(self)  -> object:
        return self.call("GET", "/v1/transactions/subscribe", stream=True)

    def create_invoice(self, amount: int, memo: str = "", expiry=(60 * 5)) -> dict:
        return self.call("POST", "/v1/invoices", data={"value": amount, "memo": memo, "expiry": expiry})
    
    @cached(cache=LRUCache(maxsize=100))
    def decode_invoice(self, invoice: str) -> dict:
        return self.call("GET", f"/v1/payreq/{invoice}")
    
    def pay_invoice(self, payment_request: str, fee_limit_sat=None, fee_limit_msat=None, allow_self_payment=True, timeout_seconds=300) -> dict:
        data = {"payment_request": payment_request, "allow_self_payment": allow_self_payment, "timeout_seconds": timeout_seconds}
        if (fee_limit_msat != None):
            data["fee_limit_msat"] = int(fee_limit_msat)
        else:
            data["fee_limit_sat"] = int(fee_limit_sat)
        
        for data in self.call("POST", "/v2/router/send", stream=True, data=data).iter_lines():
            data = loads(data).get("result")
            if (data == None):
                continue
            else:
                status = data["status"] 
                if (status == "IN_FLIGHT"):
                    continue
                elif (status == "FAILED") or (status != "SUCCEEDED"):
                    return data
                elif (status == "SUCCEEDED"):
                    return data

    def lookup_invoice(self, payment_hash: str) -> dict:
        return self.call("GET", f"/v1/invoice/{payment_hash}")
    
    def invoice_subscribe(self) -> object:
        return self.call("GET", "/v1/invoices/subscribe", stream=True)

    def channel_balance(self) -> dict:
        return self.call("GET", "/v1/balance/channels")
