import os

from jumpscale.clients.stellar import TRANSACTION_FEES
from jumpscale.loader import j
from jumpscale.packages import billing
from tests.base_tests import BaseTests


class VDCBase(BaseTests):
    @classmethod
    def setUpClass(cls):
        cls._get_env_vars()
        cls._import_wallet("test_wallet")
        cls._import_wallet("activation_wallet")
        cls._import_wallet("demos_wallet")
        cls._prepare_identity()
        cls._start_threebot_server()

    @classmethod
    def tearDownClass(cls):
        # Stop threebot server and the testing identity.
        cls.server.stop()
        j.core.identity.delete(cls.identity_name)

        # Restore the user identity
        if cls.me:
            j.core.identity.set_default(cls.me.instance_name)

    @classmethod
    def _get_env_vars(cls):
        needed_vars = ["TNAME", "EMAIL", "WORDS", "WALLET_SECRET"]
        for var in needed_vars:
            value = os.environ.get(var)
            if not value:
                raise ValueError(f"Please add {var} as environment variables")
            setattr(cls, var.lower(), value)

    @classmethod
    def _import_wallet(cls, wallet_name="test_wallet"):
        wallet = j.clients.stellar.get(wallet_name)
        wallet.secret = cls.wallet_secret
        wallet.network = "STD"
        wallet.save()
        return wallet

    @classmethod
    def _prepare_identity(cls):
        # Check if there is identity registered to set it back after the tests are finished.
        cls.me = None
        if j.core.identity.list_all() and hasattr(j.core.identity, "me"):
            cls.me = j.core.identity.me

        # Configure test identity and start threebot server.
        cls.explorer_url = "https://explorer.devnet.grid.tf/api/v1"
        cls.identity_name = j.data.random_names.random_name()
        identity = j.core.identity.new(
            cls.identity_name, tname=cls.tname, email=cls.email, words=cls.words, explorer_url=cls.explorer_url
        )
        identity.register()
        identity.set_default()

    @classmethod
    def _start_threebot_server(cls):
        cls.server = j.servers.threebot.get("default")
        path = j.sals.fs.dirname(billing.__file__)
        cls.server.packages.add(path)
        cls.server.start()

    @classmethod
    def deploy_vdc(cls, hours=1):
        cls.vdc_name = cls.random_name().lower()
        cls.password = cls.random_string()
        cls.vdc = j.sals.vdc.new(cls.vdc_name, cls.tname, cls.flavor)

        cls.info(f"Transfer needed TFT to deploy vdc for {hours} hour/s to the provisioning wallet.")
        cls.vdc_price = j.tools.zos.consumption.calculate_vdc_price(cls.flavor)
        extension_fees = TRANSACTION_FEES if hours > 1 else 0
        needed_tft = hours * (float(cls.vdc_price) / 24 / 30) + 2 * TRANSACTION_FEES + extension_fees
        # 2 transaction fees for creating the pool and extend it
        cls.vdc.transfer_to_provisioning_wallet(needed_tft, "test_wallet")

        cls.info(f"Deploy VDC for {hours} hours.")
        cls.deployer = cls.vdc.get_deployer(password=cls.password)
        minio_ak = cls.random_name().lower()
        minio_sk = cls.random_string()
        cls.timestamp_now = j.data.time.get().utcnow().timestamp
        kube_config = cls.deployer.deploy_vdc(minio_ak, minio_sk)
        if hours > 1:
            cls.deployer.renew_plan(duration=hours / 24)
        return kube_config
