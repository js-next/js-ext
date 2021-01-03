from collections import defaultdict
import hashlib
from jumpscale.clients.explorer.models import WorkloadType, ZdbNamespace, K8s, Volume, Container, DiskType
import uuid

import gevent
from jumpscale.loader import j
from jumpscale.sals.chatflows.chatflows import GedisChatBot
from jumpscale.sals.kubernetes import Manager
from jumpscale.sals.reservation_chatflow import deployer, solutions
from jumpscale.sals.zos import get as get_zos

from .kubernetes import VDCKubernetesDeployer
from .proxy import VDCProxy, VDC_PARENT_DOMAIN
from .s3 import VDCS3Deployer
from .monitoring import VDCMonitoring
from .threebot import VDCThreebotDeployer
from .public_ip import VDCPublicIP
from .scheduler import GlobalCapacityChecker, GlobalScheduler, Scheduler
from .size import *
from jumpscale.core.exceptions import exceptions
from contextlib import ContextDecorator
from jumpscale.sals.zos.billing import InsufficientFunds
import os


VDC_IDENTITY_FORMAT = "vdc_{}_{}_{}"  # tname, vdc_name, vdc_uuid
IP_VERSION = "IPv4"
IP_RANGE = "10.200.0.0/16"
MARKETPLACE_HELM_REPO_URL = "https://threefoldtech.github.io/vdc-solutions-charts/"
NO_DEPLOYMENT_BACKUP_NODES = 0


class new_vdc_context(ContextDecorator):
    def __init__(self, vdc_deployer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vdc_deployer = vdc_deployer

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.vdc_deployer.error(f"new_vdc_context: deployment failed due to exception: {exc_value}")
            self.vdc_deployer.rollback_vdc_deployment()


class VDCIdentityError(exceptions.Base):
    pass


class VDCDeployer:
    def __init__(
        self, vdc_instance, password: str = None, bot: GedisChatBot = None, proxy_farm_name: str = None, identity=None
    ):
        self.vdc_instance = vdc_instance
        self.vdc_name = self.vdc_instance.vdc_name
        self.flavor = self.vdc_instance.flavor
        self.tname = j.data.text.removesuffix(self.vdc_instance.owner_tname, ".3bot")
        self.bot = bot
        self._identity = identity
        self.password = password
        self.password_hash = None
        self.email = f"vdc_{self.vdc_instance.solution_uuid}"
        self.wallet_name = self.vdc_instance.provision_wallet.instance_name
        self.proxy_farm_name = proxy_farm_name
        self.vdc_uuid = self.vdc_instance.solution_uuid
        self.description = j.data.serializers.json.dumps({"vdc_uuid": self.vdc_uuid})
        self._log_format = f"VDC: {self.vdc_uuid} NAME: {self.vdc_name}: OWNER: {self.tname} {{}}"
        self._generate_identity()
        if not self.vdc_instance.identity_tid:
            self.vdc_instance.identity_tid = self.identity.tid
            self.vdc_instance.save()
        self._zos = None
        self._wallet = None
        self._kubernetes = None
        self._s3 = None
        self._proxy = None
        self._ssh_key = None
        self._vdc_k8s_manager = None
        self._threebot = None
        self._monitoring = None
        self._public_ip = None
        self._transaction_hashes = []

    def _retry_call(self, func, args=None, kwargs=None, timeout=5):
        args = args or list()
        kwargs = kwargs or dict()
        deadline = j.data.time.now().timestamp + timeout * 60
        while True:
            try:
                self.info(f"executing function: {func.__name__}")
                result = func(*args, **kwargs)
                self.info(f"function: {func.__name__} executed successfully. return {result}")
                return result
            except Exception as e:
                if j.data.time.now().timestamp < deadline:
                    self.warning(f"failed to execute function {func.__name__} due to error {str(e)}. retrying")
                else:
                    self.error(f"failed to execute function {func.__name__} due to error {str(e)}.")
                    raise e

    @property
    def transaction_hashes(self):
        return self._transaction_hashes

    @transaction_hashes.setter
    def transaction_hashes(self, value):
        self.info(f"adding transactions {value}")
        if isinstance(value, list):
            self._transaction_hashes += value
        self._transaction_hashes = list((set(self._transaction_hashes)))

    @property
    def public_ip(self):
        if not self._public_ip:
            self._public_ip = VDCPublicIP(self)
        return self._public_ip

    @property
    def monitoring(self):
        if not self._monitoring:
            self._monitoring = VDCMonitoring(self)
        return self._monitoring

    @property
    def threebot(self):
        if not self._threebot:
            self._threebot = VDCThreebotDeployer(self)
        return self._threebot

    @property
    def vdc_k8s_manager(self):
        if not self._vdc_k8s_manager:
            config_path = f"{j.core.dirs.CFGDIR}/vdc/kube/{self.tname}/{self.vdc_name}.yaml"
            self._vdc_k8s_manager = Manager(config_path)
        return self._vdc_k8s_manager

    @property
    def kubernetes(self):
        if not self._kubernetes:
            self._kubernetes = VDCKubernetesDeployer(self)
        return self._kubernetes

    @property
    def s3(self):
        if not self._s3:
            self._s3 = VDCS3Deployer(self)
        return self._s3

    @property
    def proxy(self):
        if not self._proxy:
            self._proxy = VDCProxy(self, self.proxy_farm_name)
        return self._proxy

    @property
    def wallet(self):
        if not self._wallet:
            wallet_name = self.wallet_name or j.core.config.get("VDC_WALLET")
            self._wallet = j.clients.stellar.get(wallet_name)
        return self._wallet

    @property
    def explorer(self):
        if self.identity:
            return self.identity.explorer
        return j.core.identity.me.explorer

    @property
    def zos(self):
        if not self._zos:
            self._zos = get_zos(self.identity.instance_name)
        return self._zos

    @property
    def ssh_key(self):
        if not self._ssh_key:
            self._ssh_key = j.clients.sshkey.get(self.vdc_name)
            vdc_key_path = j.core.config.get("VDC_KEY_PATH", "~/.ssh/id_rsa")
            self._ssh_key.private_key_path = j.sals.fs.expanduser(vdc_key_path)
            self._ssh_key.load_from_file_system()
        return self._ssh_key

    @property
    def identity(self):
        return self._identity

    def _generate_identity(self):
        # create a user identity from an old one or create a new one
        if self._identity:
            return
        self.password_hash = hashlib.md5(self.password.encode()).hexdigest()
        username = VDC_IDENTITY_FORMAT.format(self.tname, self.vdc_name, self.vdc_uuid)
        words = j.data.encryption.key_to_mnemonic(self.password_hash.encode())
        identity_name = f"vdc_ident_{self.vdc_uuid}"
        self._identity = j.core.identity.get(
            identity_name, tname=username, email=self.email, words=words, explorer_url=j.core.identity.me.explorer_url
        )
        try:
            self._identity.register()
            self._identity.save()
        except Exception as e:
            j.logger.error(f"failed to generate identity for user {identity_name} due to error {str(e)}")
            raise VDCIdentityError(f"failed to generate identity for user {identity_name} due to error {str(e)}")

    def get_pool_id(self, farm_name, cus=0, sus=0, ipv4us=0):
        cus = int(cus)
        sus = int(sus)
        ipv4us = int(ipv4us)
        self.info(f"getting pool on farm: {farm_name}, cus: {cus}, sus: {sus}, ipv4us: {ipv4us}")
        farm = self.explorer.farms.get(farm_name=farm_name)
        for pool in self.zos.pools.list():
            farm_id = deployer.get_pool_farm_id(pool.pool_id, pool, self.identity.instance_name)
            if farm_id == farm.id:
                # extend
                self.info(f"found existing pool {pool.pool_id} on farm: {farm_name}. pool: {str(pool)}")
                if not any([cus, sus, ipv4us]):
                    return pool.pool_id
                node_ids = [node.node_id for node in self.zos.nodes_finder.nodes_search(farm.id)]
                pool_info = self._retry_call(
                    self.zos.pools.extend, args=[pool.pool_id, cus, sus, ipv4us], kwargs={"node_ids": node_ids}
                )
                self.info(
                    f"extending pool {pool.pool_id} with cus: {cus}, sus: {sus}, ipv4us: {ipv4us}, reservation_info {str(pool_info)}"
                )
                self.pay(pool_info)
                return pool.pool_id
        pool_info = self._retry_call(self.zos.pools.create, args=[cus, sus, ipv4us, farm_name])
        self.info(
            f"creating new pool {pool_info.reservation_id} on farm: {farm_name}, cus: {cus}, sus: {sus}, ipv4us: {ipv4us}, reservation_info {str(pool_info)}"
        )
        self.pay(pool_info)
        return pool_info.reservation_id

    def init_vdc(self, selected_farm):
        """
        1- create 2 pool on storage farms (with the required capacity to have 50-50) as speced
        2- get (and extend) or create a pool for kubernetes controller on the network farm with small flavor
        3- get (and extend) or create a pool for kubernetes workers
        """
        farm_resources = defaultdict(lambda: dict(cus=0, sus=0, ipv4us=0))
        duration = INITIAL_RESERVATION_DURATION / 24

        def get_cloud_units(workload):
            ru = workload.resource_units()
            cloud_units = ru.cloud_units()
            return cloud_units.cu * 60 * 60 * 24 * duration, cloud_units.su * 60 * 60 * 24 * duration

        if len(ZDB_FARMS.get()) != 2:
            raise j.exceptions.Validation("incorrect config for ZDB_FARMS in size")
        for farm_name in ZDB_FARMS.get():
            zdb = ZdbNamespace()
            zdb.size = ZDB_STARTING_SIZE
            zdb.disk_type = DiskType.HDD
            _, sus = get_cloud_units(zdb)
            sus = sus * (S3_NO_DATA_NODES + S3_NO_PARITY_NODES) / 2
            farm_resources[farm_name]["sus"] += sus

        master_size = VDC_SIZE.VDC_FLAVORS[self.flavor]["k8s"]["controller_size"]
        k8s = K8s()
        k8s.size = master_size.value
        cus, sus = get_cloud_units(k8s)
        ipv4us = duration * 60 * 60 * 24
        farm_resources[NETWORK_FARM.get()]["cus"] += cus
        farm_resources[NETWORK_FARM.get()]["sus"] += sus
        farm_resources[NETWORK_FARM.get()]["ipv4us"] += ipv4us

        cont2 = Container()
        cont2.capacity.cpu = THREEBOT_CPU
        cont2.capacity.memory = THREEBOT_MEMORY
        cont2.capacity.disk_size = THREEBOT_DISK
        cont2.capacity.disk_type = DiskType.SSD
        cus = sus = 0
        n_cus, n_sus = get_cloud_units(cont2)
        cus += n_cus
        sus += n_sus
        farm_resources[selected_farm]["cus"] += cus
        farm_resources[selected_farm]["sus"] += sus

        for farm_name, cloud_units in farm_resources.items():
            pool_id = self.get_pool_id(farm_name, **cloud_units)
            self.wait_pool_payment(pool_id, trigger_sus=1)

    def deploy_vdc_network(self):
        """
        create a network for the VDC on any pool withing the ones created during initialization
        """
        for pool in self.zos.pools.list():
            scheduler = Scheduler(pool_id=pool.pool_id)
            network_success = False
            for access_node in scheduler.nodes_by_capacity(ip_version=IP_VERSION):
                self.info(f"deploying network on node {access_node.node_id}")
                network_success = True
                result = deployer.deploy_network(
                    self.vdc_name, access_node, IP_RANGE, IP_VERSION, pool.pool_id, self.identity.instance_name
                )
                for wid in result["ids"]:
                    try:
                        success = deployer.wait_workload(
                            wid,
                            breaking_node_id=access_node.node_id,
                            identity_name=self.identity.instance_name,
                            bot=self.bot,
                            cancel_by_uuid=False,
                            expiry=5,
                        )
                        network_success = network_success and success
                    except Exception as e:
                        network_success = False
                        self.error(f"network workload {wid} failed on node {access_node.node_id} due to error {str(e)}")
                        break
                if network_success:
                    self.info(
                        f"saving wireguard config to {j.core.dirs.CFGDIR}/vdc/wireguard/{self.tname}/{self.vdc_name}.conf"
                    )
                    # store wireguard config
                    wg_quick = result["wg"]
                    j.sals.fs.mkdirs(f"{j.core.dirs.CFGDIR}/vdc/wireguard/{self.tname}")
                    j.sals.fs.write_file(
                        f"{j.core.dirs.CFGDIR}/vdc/wireguard/{self.tname}/{self.vdc_name}.conf", wg_quick
                    )
                    return True

    def deploy_vdc_zdb(self, scheduler=None):
        """
        1- get pool_id of each farm from ZDB_FARMS
        2- deploy zdbs on it with half of the capacity
        """
        gs = scheduler or GlobalScheduler()
        zdb_threads = []
        for farm in ZDB_FARMS.get():
            pool_id = self.get_pool_id(farm)
            zdb_threads.append(
                gevent.spawn(
                    self.s3.deploy_s3_zdb,
                    pool_id=pool_id,
                    scheduler=gs,
                    storage_per_zdb=ZDB_STARTING_SIZE,
                    password=self.password,
                    solution_uuid=self.vdc_uuid,
                    no_nodes=(S3_NO_DATA_NODES + S3_NO_PARITY_NODES) / 2,
                )
            )
        return zdb_threads

    def deploy_vdc_kubernetes(self, farm_name, scheduler, cluster_secret):
        """
        1- deploy master
        2- extend cluster with the flavor no_nodes
        """
        gs = scheduler or GlobalScheduler()
        master_pool_id = self.get_pool_id(NETWORK_FARM.get())
        nv = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        master_size = VDC_SIZE.VDC_FLAVORS[self.flavor]["k8s"]["controller_size"]
        master_ip = self.kubernetes.deploy_master(
            master_pool_id, gs, master_size, cluster_secret, [self.ssh_key.public_key.strip()], self.vdc_uuid, nv
        )
        if not master_ip:
            self.error("failed to deploy kubernetes master")
            return
        no_nodes = VDC_SIZE.VDC_FLAVORS[self.flavor]["k8s"]["no_nodes"]
        if no_nodes < 1:
            return [master_ip]
        wids = self.kubernetes.extend_cluster(
            farm_name,
            master_ip,
            VDC_SIZE.VDC_FLAVORS[self.flavor]["k8s"]["size"],
            cluster_secret,
            [self.ssh_key.public_key.strip()],
            no_nodes,
            duration=INITIAL_RESERVATION_DURATION / 24,
            solution_uuid=self.vdc_uuid,
        )
        if not wids:
            self.error("failed to deploy kubernetes workers")
        return wids

    def _set_wallet(self, alternate_wallet_name=None):
        """
        Returns:
            old wallet name
        """
        self.info(f"using wallet: {alternate_wallet_name} instead of {self.wallet_name}")
        if not alternate_wallet_name:
            return self.wallet_name
        old_wallet_name = self.wallet_name
        self.wallet_name = alternate_wallet_name
        self._wallet = None
        return old_wallet_name

    def check_capacity(self, farm_name):
        # make sure there are available public ips
        farm = self.explorer.farms.get(farm_name=NETWORK_FARM.get())
        available_ips = False
        for address in farm.ipaddresses:
            if not address.reservation_id:
                available_ips = True
                break
        if not available_ips:
            return False

        gcc = GlobalCapacityChecker()
        # check zdb capacity
        if len(ZDB_FARMS.get()) != 2:
            raise j.exceptions.Validation("incorrect config for ZDB_FARMS in size")
        zdb_query = {
            "hru": ZDB_STARTING_SIZE,
            "no_nodes": (S3_NO_DATA_NODES + S3_NO_PARITY_NODES) / 2,
            "ip_version": "IPv6",
        }
        for farm in ZDB_FARMS.get():
            if not gcc.add_query(farm, **zdb_query):
                return False

        plan = VDC_SIZE.VDC_FLAVORS[self.flavor]

        # check kubernetes capacity
        master_query = {"farm_name": NETWORK_FARM.get(), "public_ip": True}
        master_query.update(VDC_SIZE.K8S_SIZES[plan["k8s"]["controller_size"]])
        if not gcc.add_query(**master_query):
            return False

        worker_query = {"farm_name": farm_name, "no_nodes": plan["k8s"]["no_nodes"]}
        worker_query.update(VDC_SIZE.K8S_SIZES[plan["k8s"]["size"]])
        if not gcc.add_query(**worker_query):
            return False

        # check minio container and volume capacity
        # minio_query = {
        #     "farm_name": farm_name,
        #     "cru": MINIO_CPU,
        #     "mru": MINIO_MEMORY / 1024,
        #     "sru": (MINIO_DISK / 1024) + 0.25,
        #     "ip_version": "IPv6",
        # }
        # if not gcc.add_query(**minio_query):
        #     return False

        # check threebot container capacity
        threebot_query = {
            "farm_name": farm_name,
            "cru": THREEBOT_CPU,
            "mru": THREEBOT_MEMORY / 1024,
            "sru": THREEBOT_DISK / 1024,
        }
        if not gcc.add_query(**threebot_query):
            return False

        # check trc container capacity
        trc_query = {"farm_name": farm_name, "cru": 1, "mru": 1, "sru": 0.25}
        if not gcc.add_query(**trc_query):
            return False

        return gcc.result

    def deploy_vdc(self, minio_ak, minio_sk, farm_name=None, install_monitoring_stack=False):
        """deploys a new vdc
        Args:
            minio_ak: access key for minio
            minio_sk: secret key for minio
            farm_name: where to initialize the vdc
        """
        farm_name = farm_name or PREFERED_FARM.get()
        if not self.check_capacity(farm_name):
            raise j.exceptions.Validation(
                f"There are not enough resources available to deploy your VDC of flavor `{self.flavor.value}`. To restart VDC creation, please use the refresh button on the upper right corner."
            )

        cluster_secret = self.password_hash
        self.info(f"deploying VDC flavor: {self.flavor} farm: {farm_name}")
        # if len(minio_ak) < 3 or len(minio_sk) < 8:
        #     raise j.exceptions.Validation(
        #         "Access key length should be at least 3, and secret key length at least 8 characters"
        #     )

        # initialize VDC pools
        self.bot_show_update("Initializing VDC")
        self.init_vdc(farm_name)
        self.bot_show_update("Deploying network")
        if not self.deploy_vdc_network():
            self.error("failed to deploy network")
            raise j.exceptions.Runtime("failed to deploy network")
        gs = GlobalScheduler()

        with new_vdc_context(self):
            # deploy zdbs for s3
            self.bot_show_update("Deploying ZDBs for s3")
            deployment_threads = self.deploy_vdc_zdb(gs)

            # deploy k8s cluster
            self.bot_show_update("Deploying kubernetes cluster")
            k8s_thread = gevent.spawn(self.deploy_vdc_kubernetes, farm_name, gs, cluster_secret)
            deployment_threads.append(k8s_thread)
            gevent.joinall(deployment_threads)
            for thread in deployment_threads:
                if thread.value:
                    continue
                self.error(f"failed to deploy VDC. cancelling workloads with uuid {self.vdc_uuid}")
                self.rollback_vdc_deployment()
                raise j.exceptions.Runtime(f"failed to deploy VDC. failed to deploy k8s or zdb")

            zdb_wids = deployment_threads[0].value + deployment_threads[1].value
            scheduler = Scheduler(farm_name)
            pool_id = self.get_pool_id(farm_name)

            # deploy minio container
            # self.bot_show_update("Deploying minio container")
            minio_wid = 0
            # minio_wid = self.s3.deploy_s3_minio_container(
            #     pool_id,
            #     minio_ak,
            #     minio_sk,
            #     self.ssh_key.public_key.strip(),
            #     scheduler,
            #     zdb_wids,
            #     self.vdc_uuid,
            #     self.password,
            # )
            # self.info(f"minio_wid: {minio_wid}")
            # if not minio_wid:
            #     self.error(f"failed to deploy VDC. cancelling workloads with uuid {self.vdc_uuid}")
            #     self.rollback_vdc_deployment()
            #     raise j.exceptions.Runtime(f"failed to deploy VDC. failed to deploy minio")

            # get kubernetes info
            self.bot_show_update("Preparing Kubernetes cluster configuration")
            self.vdc_instance.load_info()

            master_ip = self.vdc_instance.kubernetes[0].public_ip

            if master_ip == "::/128":
                self.error(f"couldn't get kubernetes master public ip {self.vdc_instance}")
                self.rollback_vdc_deployment()
                raise j.exceptions.Runtime(f"couldn't get kubernetes master public ip {self.vdc_instance}")

            try:
                # download kube config from master
                kube_config = self.kubernetes.download_kube_config(master_ip)
            except Exception as e:
                self.error(f"failed to download kube config due to error {str(e)}")
                self.rollback_vdc_deployment()
                raise j.exceptions.Runtime(f"failed to download kube config due to error {str(e)}")

            # deploy threebot container
            self.bot_show_update("Deploying 3Bot container")
            threebot_wid = self.threebot.deploy_threebot(minio_wid, pool_id, kube_config=kube_config)
            self.info(f"threebot_wid: {threebot_wid}")
            if not threebot_wid:
                self.error(f"failed to deploy VDC. cancelling workloads with uuid {self.vdc_uuid}")
                self.rollback_vdc_deployment()
                raise j.exceptions.Runtime(f"failed to deploy VDC. failed to deploy 3bot")

            if install_monitoring_stack:
                # deploy monitoring stack on kubernetes
                self.bot_show_update("Deploying monitoring stack")
                try:
                    self.monitoring.deploy_stack()
                except j.exceptions.Runtime as e:
                    # TODO: rollback
                    self.error(f"failed to deploy monitoring stack on VDC cluster due to error {str(e)}")

            self.bot_show_update("Updating Traefik")
            self.kubernetes.upgrade_traefik()

            return kube_config

    def get_prefix(self):
        return f"{self.tname}-{self.vdc_name}.vdc"

    def expose_s3(self, delete_previous=False):
        self.vdc_instance.load_info()
        if not self.vdc_instance.s3.minio or not self.vdc_instance.kubernetes:
            self.error(f"can't find one or more required workloads to expose s3")
            raise j.exceptions.Runtime(f"vdc {self.vdc_uuid} doesn't contain the required workloads")

        if self.vdc_instance.s3.domain:
            # s3 is already exposed
            if not delete_previous:
                # return existing subdomain
                return self.vdc_instance.s3.domain
            else:
                # delete old subdomain and re-expose
                self.zos.workloads.decomission(self.vdc_instance.s3.domain_wid)
                deployer.wait_workload_deletion(self.vdc_instance.s3.domain_wid)

        master_ip = self.vdc_instance.kubernetes[0].public_ip
        self.info(f"exposing s3 over public ip: {master_ip}")
        solution_uuid = uuid.uuid4().hex
        domain_name = self.proxy.ingress_proxy_over_managed_domain(
            f"minio",
            f"{self.tname}-{self.vdc_name}-s3",
            self.vdc_instance.s3.minio.wid,
            9000,
            master_ip,
            solution_uuid,
            force_https=True,
        )
        if not domain_name:
            solutions.cancel_solution_by_uuid(solution_uuid, self.identity.instance_name)
            self.error(f"failed to expose s3")
            return
        self.info(f"s3 exposed over domain: {domain_name}")
        return domain_name

    def add_k8s_nodes(self, flavor, farm_name=None, public_ip=False, no_nodes=1, duration=None):
        farm_name = farm_name or PREFERED_FARM.get()
        if isinstance(flavor, str):
            flavor = VDC_SIZE.K8SNodeFlavor[flavor.upper()]
        self.vdc_instance.load_info()
        master_Workload = self.zos.workloads.get(self.vdc_instance.kubernetes[0].wid)
        metadata = deployer.decrypt_metadata(master_Workload.info.metadata, self.identity.instance_name)
        meta_dict = j.data.serializers.json.loads(metadata)
        cluster_secret = meta_dict["secret"]
        self.info(f"extending kubernetes cluster on farm: {farm_name}, public_ip: {public_ip}, no_nodes: {no_nodes}")
        master_ip = self.vdc_instance.kubernetes[0].public_ip
        farm_name = farm_name if not public_ip else NETWORK_FARM.get()
        public_key = None
        try:
            public_key = self.ssh_key.public_key.strip()
        except Exception as e:
            self.warning(f"failed to fetch key pair in kubernetes extension due to error: {str(e)}")

        if not public_key:
            key_path = j.sals.fs.expanduser("~/.ssh/id_rsa.pub")
            public_key = j.sals.fs.read_file(key_path).strip()
        self.bot_show_update(f"Deploying {no_nodes} Kubernetes Nodes")
        wids = self.kubernetes.extend_cluster(
            farm_name,
            master_ip,
            flavor,
            cluster_secret,
            [public_key],
            no_nodes,
            duration=duration or INITIAL_RESERVATION_DURATION / 24,
            solution_uuid=uuid.uuid4().hex,
            public_ip=public_ip,
        )
        self.info(f"kubernetes cluster expansion result: {wids}")
        if not wids:
            raise j.exceptions.Runtime(f"all tries to deploy on farm {farm_name} has failed")
        return wids

    def delete_k8s_node(self, wid):
        return self.kubernetes.delete_worker(wid)

    def rollback_vdc_deployment(self):
        self.vdc_instance.load_info()
        if all([self.vdc_instance.threebot.domain, os.environ.get("VDC_NAME_USER"), os.environ.get("VDC_NAME_TOKEN")]):
            # delete domain record from name.com
            prefix = self.get_prefix()
            parent_domain = VDC_PARENT_DOMAIN
            nc = j.clients.name.get("VDC")
            nc.username = os.environ.get("VDC_NAME_USER")
            nc.token = os.environ.get("VDC_NAME_TOKEN")
            existing_records = nc.nameclient.list_records_for_host(parent_domain, prefix)
            if existing_records:
                for record_dict in existing_records:
                    nc.nameclient.delete_record(record_dict["fqdn"][:-1], record_dict["id"])

        solutions.cancel_solution_by_uuid(self.vdc_uuid, self.identity.instance_name)
        nv = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        if nv:
            solutions.cancel_solution(
                [workload.id for workload in nv.network_workloads], identity_name=self.identity.instance_name
            )

    def wait_pool_payment(self, pool_id, exp=5, trigger_cus=0, trigger_sus=1):
        expiration = j.data.time.now().timestamp + exp * 60
        while j.data.time.get().timestamp < expiration:
            pool = self.zos.pools.get(pool_id)
            if pool.cus >= trigger_cus and pool.sus >= trigger_sus:
                return True
            gevent.sleep(2)
        return False

    def extend_k8s_workloads(self, duration, *wids):
        """
        duration in days
        """
        duration = duration * 24 * 60 * 60
        pools_units = defaultdict(lambda: {"cu": 0, "su": 0, "ipv4us": 0})
        for wid in wids:
            workload = self.zos.workloads.get(wid)
            if workload.info.workload_type != WorkloadType.Kubernetes:
                self.warning(f"workload {wid} is not a valid kubernetes workload")
                continue
            pool_id = workload.info.pool_id
            resource_units = workload.resource_units()
            cloud_units = resource_units.cloud_units()
            pools_units[pool_id]["cu"] += cloud_units.cu * duration
            pools_units[pool_id]["su"] += cloud_units.su * duration
            if workload.public_ip:
                pools_units[pool_id]["ipv4us"] += duration

        for pool_id, units_dict in pools_units.items():
            for key in units_dict:
                units_dict[key] = int(units_dict[key])
            pool_info = self.zos.pools.extend(pool_id, **units_dict)

            self.pay(pool_info)

    def _log(self, msg, loglevel="info"):
        getattr(j.logger, loglevel)(self._log_format.format(msg))

    def info(self, msg):
        self._log(msg, "info")

    def error(self, msg):
        self._log(msg, "error")

    def warning(self, msg):
        self._log(msg, "warning")

    def critical(self, msg):
        self._log(msg, "critical")

    def bot_show_update(self, msg):
        if self.bot:
            self.bot.md_show_update(msg)

    def renew_plan(self, duration):
        """before calling
        transfer current balance in vdc wallet to deployer wallet
        transfer all amount of new payment to the VDC wallet (amount of package + amount of external nodes)
        """
        self.vdc_instance.load_info()
        pool_ids = set()
        for zdb in self.vdc_instance.s3.zdbs:
            pool_ids.add(zdb.pool_id)
        for k8s in self.vdc_instance.kubernetes:
            pool_ids.add(k8s.pool_id)
        if self.vdc_instance.s3.minio.pool_id:
            pool_ids.add(self.vdc_instance.s3.minio.pool_id)
        if self.vdc_instance.threebot.pool_id:
            pool_ids.add(self.vdc_instance.threebot.pool_id)
        self.info(f"renew plan with pools: {pool_ids}")
        for pool_id in pool_ids:
            pool = self.zos.pools.get(pool_id)
            sus = pool.active_su * duration * 60 * 60 * 24
            cus = pool.active_cu * duration * 60 * 60 * 24
            ipv4us = pool.active_ipv4 * duration * 60 * 60 * 24
            pool_info = self.zos.pools.extend(pool_id, int(cus), int(sus), int(ipv4us))
            self.info(
                f"renew plan: extending pool {pool_id}, sus: {sus}, cus: {cus}, reservation_id: {pool_info.reservation_id}"
            )
            self.pay(pool_info)
        self.vdc_instance.updated = j.data.time.utcnow().timestamp
        if self.vdc_instance.is_blocked:
            self.vdc_instance.revert_grace_period_action()

    def pay(self, pool_info):
        deadline = j.data.time.now().timestamp + 5 * 60
        success = False
        while j.data.time.now().timestamp < deadline and not success:
            try:
                self.transaction_hashes += self.zos.billing.payout_farmers(self.wallet, pool_info)
                success = True
            except InsufficientFunds as e:
                raise e
            except Exception as e:
                self.warning(f"failed to submit payment to stellar due to error {str(e)}")
                gevent.sleep(3)
        if not success:
            raise j.exceptions.Runtime(f"failed to submit payment to stellar in time for {pool_info}")
