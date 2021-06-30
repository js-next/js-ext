from enum import Enum
from jumpscale.core.base import fields

from . import Capacity, Data, DeviceType, Result


class Mode(Enum):
    USER = "user"
    SEQ = "seq"


class ZDB(Data):
    size = fields.Integer(min=1)
    mode = fields.Enum(Mode)
    password_encrypted = fields.String()
    disk_type = fields.Enum(DeviceType)
    public = fields.Boolean()

    @property
    def capacity(self):
        if self.disk_type == DeviceType.HDD:
            return Capacity(HRU=self.size)
        else:
            return Capacity(SRU=self.size)


class ZDBResult(Result):
    namespace = fields.String()
    ips = fields.List(fields.IPAddress())
    port = fields.Port()
