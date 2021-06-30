from jumpscale.core.base import Base, fields
from jumpscale.core.base.fields import ValidationError

from . import Capacity, Data, Result


SIZES = {
    1: {"cru": 1, "mru": 2, "sru": 50,},
    2: {"cru": 2, "mru": 4, "sru": 100,},
    3: {"cru": 2, "mru": 8, "sru": 25,},
    4: {"cru": 2, "mru": 5, "sru": 50,},
    5: {"cru": 2, "mru": 8, "sru": 200,},
    6: {"cru": 4, "mru": 16, "sru": 50,},
    7: {"cru": 4, "mru": 16, "sru": 100,},
    8: {"cru": 4, "mru": 16, "sru": 400,},
    9: {"cru": 8, "mru": 32, "sru": 100,},
    10: {"cru": 8, "mru": 32, "sru": 200,},
    11: {"cru": 8, "mru": 32, "sru": 800,},
    12: {"cru": 1, "mru": 64, "sru": 200,},
    13: {"cru": 1, "mru": 64, "sru": 400,},
    14: {"cru": 1, "mru": 64, "sru": 800,},
    15: {"cru": 1, "mru": 2, "sru": 25,},
    16: {"cru": 2, "mru": 4, "sru": 50,},
    17: {"cru": 4, "mru": 8, "sru": 50,},
    18: {"cru": 1, "mru": 1, "sru": 25,},
}


class Kubernetes(Data):
    SKIP_CHALLENGE = ["datastore_endpoint", "disable_default_ingress"]

    def validate_size(size):
        if size not in SIZES:
            raise ValidationError("size is not supported")

    size = fields.Integer(validators=[validate_size])
    cluster_secret = fields.String()
    network_id = fields.String()
    ip = fields.IPAddress()
    master_ips = fields.List(fields.IPAddress())
    ssh_keys = fields.List(fields.String())
    public_ip = fields.String()
    datastore_endpoint = fields.String()
    disable_default_ingress = fields.Boolean()

    @property
    def capacity(self):
        return Capacity(**SIZES[self.size])


class KubernetesResult(Result):
    id = fields.String()
    ip = fields.String()
