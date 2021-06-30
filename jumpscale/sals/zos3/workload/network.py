from jumpscale.core.base import fields

from . import Data


class Peer(Data):
    def validate_allowed_ips(value):
        if value is None:
            value = []

        if not len(value):
            raise fields.ValidationError("allowed ips cannot be empty")

    wireguard_public_key = fields.String(required=True, allow_empty=False)
    endpoint = fields.String(default="")
    subnet = fields.IPRange(allow_empty=False)
    allowed_ips = fields.List(fields.IPRange(), validators=[validate_allowed_ips])


class Network(Data):
    SKIP_CHALLENGE = ["wiregaurd_listen_port"]

    name = fields.String(required=True, allow_empty=False)
    ip_range = fields.IPRange(required=True, allow_empty=False)
    subnet = fields.IPRange(required=True, allow_empty=False)
    wireguard_private_key_encrypted = fields.String(required=True, allow_empty=False)
    wireguard_listen_port = fields.Port()
    peers = fields.List(fields.Object(Peer))
