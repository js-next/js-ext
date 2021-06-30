from jumpscale.core.base import Base, fields

from . import Capacity, Data, DeviceType, Result


class Volume(Data):
    size = fields.Integer(min=1)
    type = fields.Enum(DeviceType)

    @property
    def capacity(self):
        c = Capacity()

        if self.type == DeviceType.HDD:
            c.hru = size
        else:
            c.sru = size

        return c


class VolumeResult(Result):
    volume_id = fields.String()
