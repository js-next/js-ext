from gevent import monkey

monkey.patch_all(subprocess=False)  # noqa: E402

import os
from jumpscale.loader import j
from jumpscale.sals.vdc.deployer import VDC_IDENTITY_FORMAT
import gevent
import requests

"""
minimal entrypoint for a 3bot container to run as part of VDC deployments on k8s


Required env variables:
- VDC_NAME  -> for identity generation
- VDC_UUID  -> for VDC workload identification
- VDC_OWNER_TNAME  -> for identity generation
- VDC_EMAIL ->  for identity generation


- VDC_PASSWORD_HASH  -> for identity generation
- EXPLORER_URL  -> for identity generation and wallet network
- VDC_MINIO_ADDRESS  -> used for monitoring to trigger auto-top up and reconfig
- VDC_S3_MAX_STORAGE  -> used for auto top up
- S3_AUTO_TOPUP_FARMS  -> used for auto top up
- VDC_INSTANCE -> json string from the VDC instance on deployer
- PREPAID_WALLET_SECRET -> secret for prepaid wallet
- PROVISIONING_WALLET_SECRET -> secret for provisioning wallet


Role:
1- define the identity
2- import wallet
3- run auto-top up service
"""

VDC_PASSWORD_HASH = os.environ.get("VDC_PASSWORD_HASH")
EXPLORER_URL = os.environ.get("EXPLORER_URL")
VDC_S3_MAX_STORAGE = os.environ.get("VDC_S3_MAX_STORAGE")
S3_AUTO_TOPUP_FARMS = os.environ.get("S3_AUTO_TOPUP_FARMS")
VDC_MINIO_ADDRESS = os.environ.get("VDC_MINIO_ADDRESS")
MONITORING_SERVER_URL = os.environ.get("MONITORING_SERVER_URL")
TEST_CERT = os.environ.get("TEST_CERT", "false")
VDC_INSTANCE = os.environ.get("VDC_INSTANCE")
VDC_EMAIL = os.environ.get("VDC_EMAIL")
KUBE_CONFIG = os.environ.get("KUBE_CONFIG")
PROVISIONING_WALLET_SECRET = os.environ.get("PROVISIONING_WALLET_SECRET")
PREPAID_WALLET_SECRET = os.environ.get("PREPAID_WALLET_SECRET")


vdc_dict = j.data.serializers.json.loads(VDC_INSTANCE)
vdc = j.sals.vdc.from_dict(vdc_dict)

VDC_INSTANCE_NAME = vdc.instance_name
os.environ.putenv("VDC_INSTANCE_NAME", VDC_INSTANCE_NAME)

VDC_VARS = {
    "VDC_PASSWORD_HASH": VDC_PASSWORD_HASH,
    "EXPLORER_URL": EXPLORER_URL,
    "VDC_S3_MAX_STORAGE": VDC_S3_MAX_STORAGE,
    "S3_AUTO_TOPUP_FARMS": S3_AUTO_TOPUP_FARMS,
    "VDC_MINIO_ADDRESS": VDC_MINIO_ADDRESS,
    "MONITORING_SERVER_URL": MONITORING_SERVER_URL,
    "TEST_CERT": TEST_CERT,
    "VDC_INSTANCE": VDC_INSTANCE,
    "VDC_EMAIL": VDC_EMAIL,
    "KUBE_CONFIG": KUBE_CONFIG,
    "PROVISIONING_WALLET_SECRET": os.environ.get("PROVISIONING_WALLET_SECRET"),
    "PREPAID_WALLET_SECRET": os.environ.get("PREPAID_WALLET_SECRET"),
    "VDC_INSTANCE_NAME": VDC_INSTANCE_NAME,
}


for key, value in VDC_VARS.items():
    # TODO: bring back when merging to development branch
    # if not value:
    #     raise j.exceptions.Validation(f"MISSING ENVIRONMENT VARIABLES. {key} is not set")
    j.sals.process.execute(f"""echo "{key}='{value}'" >> /root/.bashrc""")


vdc_dict = j.data.serializers.json.loads(VDC_INSTANCE)


username = VDC_IDENTITY_FORMAT.format(vdc_dict["owner_tname"], vdc_dict["vdc_name"], vdc_dict["solution_uuid"])
words = j.data.encryption.key_to_mnemonic(VDC_PASSWORD_HASH.encode())

identity = j.core.identity.get(
    f"vdc_ident_{vdc_dict['solution_uuid']}", tname=username, email=VDC_EMAIL, words=words, explorer_url=EXPLORER_URL
)

identity.register()
identity.save()
identity.set_default()

if not j.sals.vdc.list_all():
    vdc = j.sals.vdc.from_dict(vdc_dict)
else:
    vdc = j.sals.vdc.find(list(j.sals.vdc.list_all())[0])

network = "STD"

if "testnet" in EXPLORER_URL or "devnet" in EXPLORER_URL:
    network = "TEST"

j.core.config.set(
    "S3_AUTO_TOP_SOLUTIONS",
    {
        "farm_names": S3_AUTO_TOPUP_FARMS.split(","),
        "extension_size": 10,
        "max_storage": int(VDC_S3_MAX_STORAGE),
        "threshold": 0.7,
        "clear_threshold": 0.4,
        "targets": {
            vdc.vdc_name: {
                "minio_api_url": f"http://{VDC_MINIO_ADDRESS}:9000",
                "healing_url": f"http://{VDC_MINIO_ADDRESS}:9010",
            }
        },
    },
)


j.core.config.set("VDC_THREEBOT", True)

j.config.set("SEND_REMOTE_ALERTS", True)

# TODO: remove empty exception when merging with development branch
try:
    from register_dashboard import register_dashboard

    register_dashboard()
except:
    pass

deadline = j.data.time.now().timestamp + 10 * 60
while not vdc.threebot.domain and j.data.time.now().timestamp < deadline:
    j.logger.info("wating for threebot domain reservation")
    vdc.load_info()
    gevent.sleep(10)

j.core.config.set("OVER_PROVISIONING", True)
server = j.servers.threebot.get("default")
server.packages.add("/sandbox/code/github/threefoldtech/js-sdk/jumpscale/packages/billing")
if TEST_CERT != "true":
    server.packages.add(
        "/sandbox/code/github/threefoldtech/js-sdk/jumpscale/packages/vdc_dashboard",
        admins=[f"{vdc.owner_tname}.3bot"],
        domain=vdc.threebot.domain,
    )
else:
    server.packages.add(
        "/sandbox/code/github/threefoldtech/js-sdk/jumpscale/packages/vdc_dashboard", admins=[f"{vdc.owner_tname}.3bot"]
    )
server.save()

j.sals.process.execute("cat /root/.ssh/authorized_keys > /root/.ssh/id_rsa.pub")
j.sals.fs.mkdirs(f"{j.core.dirs.CFGDIR}/vdc/kube/{vdc.owner_tname}")
j.sals.fs.write_file(f"{j.core.dirs.CFGDIR}/vdc/kube/{vdc.owner_tname}/{vdc.vdc_name}.yaml", KUBE_CONFIG)

j.sals.fs.mkdirs("/root/.kube")
j.sals.fs.write_file("/root/.kube/config", KUBE_CONFIG)

# Register provisioning and prepaid wallets

wallet = j.clients.stellar.get(
    name=f"prepaid_wallet_{vdc.solution_uuid}", secret=PREPAID_WALLET_SECRET, network=network
)
wallet.save()

wallet = j.clients.stellar.get(
    name=f"provision_wallet_{vdc.solution_uuid}", secret=PROVISIONING_WALLET_SECRET, network=network
)
wallet.save()
