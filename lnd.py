from cachetools import cached, LRUCache
from requests import request
from json import loads, dumps

class Lnd:

    def __init__(self, url: str, macaroon: str, certificate: str = None) -> None:
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
    
    def get_estimate_fee(self, address: str, amount: int, target_conf=144) -> dict:
        return self.call("GET", f'/v1/transactions/fee?target_conf={target_conf}&AddrToAmount[{address}]={amount}')

    def send_coins(self, address: str, amount: int, sat_per_vbyte: int = 1, spend_unconfirmed=False) -> dict:
        data = {"addr": address, "amount": amount, "sat_per_vbyte": sat_per_vbyte, "spend_unconfirmed": spend_unconfirmed}
        return self.call("POST", "/v1/transactions", data=data)
    
    def get_address(self, type_address="", account="") -> dict:
        query = {}
        if (type_address) and (account):
            query.update({"type": type_address, "account": account})
        return self.call("GET", "/v1/newaddress", query=query)
    
    def channels_balance(self) -> dict:
        return self.call("GET", "/v1/balance/channels")
    
    def transactions_subscribe(self)  -> object:
        return self.call("GET", "/v1/transactions/subscribe", stream=True)

    def create_invoice(self, amount: int, memo: str, expiry=(60 * 5)) -> dict:
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
