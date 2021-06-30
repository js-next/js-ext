from enum import Enum
from io import StringIO

from jumpscale.core.base import Base, fields


class Challengeable(Base):
    """
    a base type to build challenges from fields

    ordering of field definition is a mandatory, to exclude any field from
    the challenge string, just add its name to `SKIP_CHALLENGE` list.
    """

    # field names to be excluded from the challenge string
    SKIP_CHALLENGE = []

    def is_challengeable(self, value_or_type):
        if isinstance(value_or_type, type):
            return issubclass(value_or_type, Challengeable)
        return isinstance(value_or_type, Challengeable)

    def get_value_challenge(self, value):
        if isinstance(value, dict):
            return "".join([f"{k}={v}" for k, v in value.items()])

        if isinstance(value, (list, tuple, set)):
            return "".join(map(str, value))

        if isinstance(value, bool):
            return str(value).lower()

        return str(value)

    def challenge(self, io):
        all_fields = self._get_fields()

        for name, field in all_fields.items():
            if name in self.SKIP_CHALLENGE:
                continue

            value = getattr(self, name)
            if self.is_challengeable(value):
                value.challenge(io)
                continue

            if isinstance(field, fields.List):
                if isinstance(field.field, fields.Object):
                    if self.is_challengeable(field.field.type):
                        for obj in value:
                            obj.challenge(io)
                        continue

            # write raw value to io
            raw_value = field.to_raw(value)
            io.write(self.get_value_challenge(raw_value))


class Result(Base):
    pass


class DeviceType(Enum):
    HDD = "hdd"
    SSD = "ssd"


class Capacity(Base):
    cru = fields.Integer()
    sru = fields.Integer()
    hru = fields.Integer()
    mru = fields.Integer()
    ipv4u = fields.Integer()


class WorkloadType(Enum):
    Container = "container"
    Volume = "volume"
    Network = "network"
    ZDB = "zdb"
    Kubernetes = "kubernetes"
    PublicIP = "ipv4"


class Data(Challengeable):
    @property
    def capacity(self):
        return Capacity()


class Workload(Challengeable):
    SKIP_CHALLENGE = ["id", "created", "to_delete", "result", "signature"]

    def get_signature(self):
        io = StringIO()
        self.challenge(io)
        challenge = io.getvalue()
        # should return hex(ed25519.sign(sk, challenge)
        # sk => identity secret
        return challenge

    def data_updated(self, value):
        # update type according to workload
        self.type = WorkloadType[type(value).__name__].value

    version = fields.Integer()
    user_id = fields.String(required=True, allow_empty=False)
    type = fields.Enum(WorkloadType)
    metadata = fields.String()
    description = fields.String()
    data = fields.Object(Data, on_update=data_updated)

    id = fields.String()
    created = fields.DateTime()
    to_delete = fields.Boolean()
    signature = fields.String(compute=get_signature)
    result = fields.Object(Result)
