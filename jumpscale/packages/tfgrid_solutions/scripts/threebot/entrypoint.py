from gevent import monkey

monkey.patch_all(subprocess=False)  # noqa: E402

import os
import requests
from jumpscale.loader import j
from jumpscale.packages.backup.actors.threebot_deployer import Backup
from jumpscale.packages.admin.actors.wallet import Wallet

EXTENSION_WALLET = "mainnet_Wallet"


def create_mainnet_wallet(wallet_name):
    wallet_actor = Wallet()
    try:
        wallet_actor.create_wallet(wallet_name)
    except Exception:
        pass


def main():
    BACKUP_ACTOR = Backup()
    instance_name = os.environ.get("INSTANCE_NAME")
    threebot_name = os.environ.get("THREEBOT_NAME")
    domain = os.environ.get("DOMAIN")
    backup_password = os.environ.get("BACKUP_PASSWORD", None)
    test_cert = os.environ.get("TEST_CERT")

    tname = f"{threebot_name}_{instance_name}"
    email = f"{tname}@threefold.me"
    words = j.data.encryption.key_to_mnemonic(backup_password.encode().zfill(32))

    new = True

    resp = requests.get("https://explorer.grid.tf/api/v1/users", params={"name": tname})
    if resp.json():
        new = False

    j.logger.info("Generating guest identity ...")
    identity_main = j.core.identity.get(
        "main", tname=tname, email=email, words=words, explorer_url="https://explorer.grid.tf/api/v1"
    )
    identity_test = j.core.identity.get(
        "test", tname=tname, email=email, words=words, explorer_url="https://explorer.testnet.grid.tf/api/v1"
    )

    identities = [identity_main, identity_test]
    for identity in identities:
        identity.admins.append(f"{threebot_name}.3bot")
        identity.register()
        identity.save()

    j.core.identity.set_default("main")
    create_mainnet_wallet(EXTENSION_WALLET)
    j.config.set("HOSTED_3BOT", True)
    j.config.set("ANNOUNCED", False)
    if backup_password:
        # Seprate the logic of wallet creation in case of stellar failure it still takes the backup
        # Create a funded wallet to the threebot testnet
        try:
            j.clients.stellar.create_testnet_funded_wallet(f"{threebot_name}_{instance_name}")
        except Exception as e:
            j.logger.error(str(e))

        # Sanitation for the case user deleted his old backups!
        try:
            BACKUP_ACTOR.init(backup_password, new=False)
        except Exception as e:
            new = True
            j.logger.warning(f"{str(e)}: Reinitalizing backup for new user")

        try:
            BACKUP_ACTOR.init(backup_password, new=new)
            if not new:
                snapshots = j.data.serializers.json.loads(BACKUP_ACTOR.snapshots())
                if snapshots.get("data"):
                    j.logger.info("Restoring backup ...")
                    BACKUP_ACTOR.restore()
            else:
                j.logger.info("Taking backup ...")
                BACKUP_ACTOR.backup(tags="init")
        except Exception as e:
            j.logger.error(str(e))

    j.logger.info("Starting threebot ...")

    server = j.servers.threebot.get("default")
    if test_cert == "false":
        server.domain = domain
        server.email = email
        server.save()


if __name__ == "__main__":
    main()
