from jumpscale.core.base import StoredFactory


def export_module_as():
    from .client import Client

    return StoredFactory(Client)
