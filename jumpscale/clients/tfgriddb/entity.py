from .modules.tfgrid import TFGrid


class Entity(TFGrid):
    def sign(self, name, country_id, city_id):
        out = bytearray()
        out += name.encode()
        out += country_id.to_bytes(4, "big")
        out += city_id.to_bytes(4, "big")
        return self.client.keypair.sign(out.decode())[2:]

    def create(self, name, country_id, city_id):
        signature = self.sign(name, country_id, city_id)
        target = self.client.keypair.public_key
        return self.create_entity(name=name, city_id=city_id, country_id=country_id, target=target, signature=signature)
