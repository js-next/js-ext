from . import call, Module


class Balances(Module):
    @call
    def transfer(self, *, dest, value):
        """transfer the amount of `value` to `dest`"""
