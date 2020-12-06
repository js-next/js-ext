from jumpscale.loader import j
from jumpscale.packages.vdc.utils import tranfer_prepaid_to_provision_wallet
from jumpscale.tools.servicemanager.servicemanager import BackgroundService


class TransferPrepaidToProvisionWallet(BackgroundService):
    def __init__(self, name="auto_transfer_funds_from_prepaid_provision_wallet", interval=60 * 60, *args, **kwargs):
        """Provisioning wallet service that will run every hour to transfer
        funds from prepaid to provision wallet
        """
        super().__init__(name, interval, *args, **kwargs)

    def job(self):
        tranfer_prepaid_to_provision_wallet()
        j.logger.info("Auto transfer funds from prepad to provision wallet")


service = TransferPrepaidToProvisionWallet()
