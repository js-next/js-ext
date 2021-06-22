from substrateinterface import Keypair, KeypairType, SubstrateInterface

from jumpscale.core.base import Base, fields

from .modules.balances import Balances
from .entity import Entity


class Client(Base):
    def reset_interface(self, value=None):
        self._interface = None

    def reset_keypair(self, value=None):
        self._keypair = None

    url = fields.URL(required=True, allow_empty=False, on_update=reset_interface)
    words = fields.Secret(required=True, allow_empty=False, on_update=reset_keypair)
    types = fields.Typed(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.reset_interface()
        self.reset_keypair()

        self.balances = Balances(self)
        self.entity = Entity(self)

    @property
    def interface(self):
        if not self._interface:
            self._interface = SubstrateInterface(url=self.url, ss58_format=42, type_registry_preset="default")
        return self._interface

    @property
    def keypair(self):
        if not self._keypair:
            self._keypair = Keypair.create_from_mnemonic(self.words, crypto_type=KeypairType.ED25519)
        return self._keypair

    @property
    def address(self):
        return self.keypair.ss58_address
