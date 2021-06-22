from . import call, Module


class TFGrid(Module):
    NAME = "TfgridModule"

    @call
    def create_entity(self, *, name, city_id, country_id, target, signature):
        """create an entity"""
