from hashlib import new
from jumpscale.sals.reservation_chatflow.deployer import DeploymentFailed
from .base_component import VDCBaseComponent
from .size import THREEBOT_CPU, THREEBOT_MEMORY, THREEBOT_DISK, VDC_FLAFORS, S3_ZDB_SIZES, S3_AUTO_TOPUP_FARMS
from jumpscale.loader import j
from jumpscale.clients.explorer.models import WorkloadType
from .scheduler import Scheduler
from jumpscale.sals.reservation_chatflow import deployer


THREEBOT_FLIST = "https://hub.grid.tf/ahmed_hanafy_1/ahmedhanafy725-js-sdk-latest.flist"


class VDCThreebotDeployer(VDCBaseComponent):
    def deploy_threebot(self, minio_wid, pool_id):
        workload = self.zos.workloads.get(minio_wid)
        if workload.info.workload_type != WorkloadType.Container:
            raise j.exceptions.Validation(f"workload {minio_wid} is not container workload")
        minio_ip_address = workload.network_connection[0].ipaddress
        secret_env = {
            "VDC_OWNER_TNAME": self.vdc_deployer.tname,
            "VDC_EMAIL": self.vdc_deployer.email,
            "VDC_PASSWORD_HASH": self.vdc_deployer.password_hash,
            "VDC_WALLET_SECRET": self.vdc_deployer.wallet.secret,
        }
        env = {
            "VDC_NAME": self.vdc_name,
            "VDC_UUID": self.vdc_uuid,
            "EXPLORER_URL": j.core.identity.me.explorer_url,
            "VDC_S3_MAX_STORAGE": str(S3_ZDB_SIZES[VDC_FLAFORS[self.vdc_deployer.flavor]["s3"]["size"]]["sru"]),
            "S3_AUTO_TOPUP_FARMS": ",".join(S3_AUTO_TOPUP_FARMS),
            "VDC_MINIO_ADDRESS": minio_ip_address,
            "SDK_VERSION": "development_vdc",  # TODO: change when merged
            "SSHKEY": self.vdc_deployer.ssh_key.public_key.strip(),
            "MINIMAL": "true",
        }

        scheduler = Scheduler(pool_id=pool_id)
        for node in scheduler.nodes_by_capacity(THREEBOT_CPU, THREEBOT_DISK / 1024, THREEBOT_MEMORY / 1024):
            network_view = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
            self.vdc_deployer.info(f"vdc threebot: node {node.node_id} selected")
            result = deployer.add_network_node(
                network_view.name, node, pool_id, network_view, self.bot, self.identity.instance_name
            )
            self.vdc_deployer.info(f"vdc threebot network update result for node {node.node_id} is {result}")
            if result:
                network_updated = True
                try:
                    for wid in result["ids"]:
                        success = deployer.wait_workload(
                            wid,
                            self.bot,
                            expiry=5,
                            breaking_node_id=node.node_id,
                            identity_name=self.identity.instance_name,
                        )
                        network_updated = network_updated and success
                    if not network_updated:
                        raise DeploymentFailed()
                except DeploymentFailed:
                    self.vdc_deployer.error(f"failed to deploy network on node {node.node_id}")
                    continue
            network_view = network_view.copy()
            ip_address = network_view.get_free_ip(node)
            self.vdc_deployer.info(f"vdc threebot container ip address {ip_address}")
            if not ip_address:
                continue

            log_config = j.core.config.get("VDC_LOG_CONFIG", {})
            if log_config:
                log_config["channel_name"] = self.vdc_instance.instance_name

            wid = deployer.deploy_container(
                pool_id=pool_id,
                node_id=node.node_id,
                network_name=network_view.name,
                ip_address=ip_address,
                flist=THREEBOT_FLIST,
                env=env,
                cpu=THREEBOT_CPU,
                memory=THREEBOT_MEMORY,
                disk_size=THREEBOT_DISK,
                secret_env=secret_env,
                identity_name=self.identity.instance_name,
                description=self.vdc_deployer.description,
                form_info={"chatflow": "threebot", "Solution name": self.vdc_name},
                log_config=log_config,
            )
            self.vdc_deployer.info(f"vdc threebot container wid: {wid}")
            try:
                success = deployer.wait_workload(wid, self.bot, identity_name=self.identity.instance_name)
                if success:
                    return wid
                raise DeploymentFailed()
            except DeploymentFailed:
                self.vdc_deployer.error(f"failed to deploy threebot container on node: {node.node_id} wid: {wid}")
                continue
