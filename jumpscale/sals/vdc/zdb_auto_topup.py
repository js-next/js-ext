import re
from jumpscale.loader import j
import math
from .s3_auto_topup import get_zdb_farms_distribution, get_farm_pool_id, extend_zdbs


class ZDBMonitor:
    def __init__(self, vdc_instance) -> None:
        self.vdc_instance = vdc_instance

    @property
    def zdbs(self):
        if not self.vdc_instance.s3.zdbs:
            self.vdc_instance.load_info()
        return self.vdc_instance.s3.zdbs

    @property
    def zdb_total_size(self):
        size = 0
        for zdb in self.zdbs:
            size += zdb.size
        return size

    def is_extend_triggered(self, threshold=0.7, limit=None):
        """
        check if zdbs need to be extended according to threshold (0.7) and maximum limit in GB if specified
        """
        util = self.check_utilization()
        if util < threshold:
            return False, util
        if limit and self.zdb_total_size >= limit:
            return False, util
        return True, util

    def check_utilization(self):
        """
        connect to all zdbs and check data utilization
        """
        used_size = 0
        for zdb in self.zdbs:
            client = j.clients.redis.get(f"zdb_{zdb.wid}")
            client.hostname = zdb.ip_address
            client.port = zdb.port
            try:
                result = client.execute_command("nsinfo", zdb.namespace)
            except Exception as e:
                j.logger.error(f"failed to fetch namespace info for zdb: {zdb} due to error {str(e)}")
                continue
            nsinfo = self._parse_info(result.decode())
            if not all(["data_size_bytes" in nsinfo, "data_limits_bytes" in nsinfo]):
                j.logger.warning(f"missing data_size and data_limits keys in namespace info for zdb: {zdb}")
                continue
            used_size += float(nsinfo["data_size_bytes"]) / 1024 ** 3
        return used_size / self.zdb_total_size

    def _parse_info(self, info: str):
        result = {}
        for line in info.splitlines():
            splits = line.split(": ")
            if len(splits) != 2:
                continue
            key, val = splits[0], splits[1]
            result[key] = val
        return result

    def get_extension_capacity(self, threshold=0.7, clear_threshold=0.4, limit=None):
        triggered, util = self.is_extend_triggered(threshold, limit)
        j.logger.info(f"zdbs current utilization: {util} extension triggered: {triggered}")
        if not triggered:
            return 0
        total_storage = self.zdb_total_size
        used_storage = util * total_storage
        required_capacity = (used_storage / clear_threshold) - total_storage
        j.logger.info(
            f"zdb stats: total_storage: {total_storage}, used_storage: {used_storage}, required_capacity: {required_capacity}, limit: {limit}, clear_threshold: {clear_threshold}"
        )
        if limit and required_capacity + used_storage > limit:
            required_capacity = limit - used_storage

        if required_capacity < 1:
            return 0

        return required_capacity

    def get_password(self):
        zos = j.sals.zos.get()
        for zdb in self.zdbs:
            workload = zos.workloads.get(zdb.wid)
            metadata = j.sals.reservation_chatflow.deployer.decrypt_metadata(workload.info.metadata)
            try:
                metadata_dict = j.data.serializers.json.loads(metadata)
            except Exception as e:
                continue
            if not metadata_dict.get("password"):
                continue
            return metadata_dict["password"]
        raise j.exceptions.Runtime("couldn't get password for any zdb of vdc")

    def extend(self, required_capacity, farm_names, extension_size=10):
        password = self.get_password()
        no_zdbs = math.floor(required_capacity / extension_size)
        if no_zdbs < 1:
            return
        solution_uuid = self.vdc_instance.solution_uuid
        farm_names = get_zdb_farms_distribution(solution_uuid, farm_names, no_zdbs)
        pool_ids = []
        farm_pools = {}
        for farm_name in farm_names:
            pool_id = farm_pools.get(farm_name)
            if not pool_id:
                pool_id = get_farm_pool_id(farm_name)
                farm_pools[farm_name] = pool_id
            pool_ids.append(pool_id)
        wids, _ = extend_zdbs(
            self.vdc_instance.vdc_name,
            pool_ids,
            solution_uuid,
            password,
            self.vdc_instance.get_pools_expiration(),
            extension_size,
            wallet_name=self.vdc_instance.provision_wallet.instance_name,
        )
        j.logger.info(f"zdbs extended with wids: {wids}")
        if len(wids) != no_zdbs:
            j.logger.error(f"AUTO_TOPUP: couldn't deploy all required zdbs. successful workloads {wids}")
