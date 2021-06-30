from jumpscale.core.base import Base, fields

from . import Capacity, Data, Result


class PublicIP(Data):
    NAME = "ipv4"

    ip = fields.IPAddress(required=True)

    @property
    def capacity(self):
        return Capacity(ipv4u=1)


class PublicIPResult(Result):
    ip = fields.IPAddress(required=True)
