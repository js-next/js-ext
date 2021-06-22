"""base module implementation"""
from functools import wraps

from substrateinterface.exceptions import SubstrateRequestException


class CallException(Exception):
    pass


def call(func):
    @wraps(func)
    def wrapper(self, **kwargs):
        return self.call(func.__name__, **kwargs)

    return wrapper


class Module:
    NAME = None

    def __init__(self, client):
        self.client = client

    @property
    def name(self):
        if self.NAME:
            return self.NAME
        return self.__class__.__name__

    def call(self, func_name, **kwargs):
        interface = self.client.interface

        call = interface.compose_call(call_module=self.name, call_function=func_name, call_params=kwargs)

        extrinsic = interface.create_signed_extrinsic(call=call, keypair=self.client.keypair)

        try:
            receipt = interface.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            if not receipt.is_success:
                raise CallException(receipt.error_message)
            return receipt
        except SubstrateRequestException as e:
            raise CallException from e
