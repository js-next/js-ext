import math
import uuid

from jumpscale.loader import j
from jumpscale.sals.reservation_chatflow import deployer
from jumpscale.sals.reservation_chatflow.deployer import DeploymentFailed

from .base_component import VDCBaseComponent
from .scheduler import CapacityChecker, Scheduler
from .size import *


class VDCKubernetesDeployer(VDCBaseComponent):
    def __init__(self, *args, **kwrags) -> None:
        super().__init__(*args, **kwrags)

    def deploy_kubernetes(self, pool_id, scheduler, k8s_size_dict, cluster_secret, ssh_keys):
        self.vdc_deployer.info(f"deploying kubernetes with size_dict: {k8s_size_dict}")
        no_nodes = k8s_size_dict["no_nodes"]
        master_ip = None
        network_view = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        nodes_generator = scheduler.nodes_by_capacity(**K8S_SIZES[k8s_size_dict["size"]])

        # deploy master
        master_ip = self._deploy_master(
            pool_id, nodes_generator, k8s_size_dict["size"], cluster_secret, ssh_keys, self.vdc_uuid, network_view
        )
        self.vdc_deployer.info(f"kubernetes master ip: {master_ip}")
        if not master_ip:
            self.vdc_deployer.error("failed to deploy master")
            return
        return self._add_workers(
            pool_id,
            nodes_generator,
            k8s_size_dict["size"],
            cluster_secret,
            ssh_keys,
            self.vdc_uuid,
            network_view,
            master_ip,
            no_nodes,
        )

    def _preprare_extension_pool(self, farm_name, k8s_flavor, no_nodes, duration):
        """
        returns pool id after extension with enough cloud units
        duration in seconds
        """
        k8s_resources_dict = K8S_SIZES[k8s_flavor]
        cus, sus = deployer.calculate_capacity_units(**k8s_resources_dict)
        cus = cus * duration * no_nodes
        sus = sus * duration * no_nodes

        farm = self.explorer.farms.get(farm_name=farm_name)
        pool_id = None
        for pool in self.zos.pools.list():
            farm_id = deployer.get_pool_farm_id(pool.pool_id, pool, self.identity.instance_name)
            if farm_id == farm.id:
                pool_id = pool.pool_id
                break

        trigger_cus = 0
        trigger_sus = 1
        if not pool_id:
            pool_info = self.zos.pools.create(math.ceil(cus), math.ceil(sus), farm_name)
            pool_id = pool_info.reservation_id
            self.vdc_deployer.info(f"new pool {pool_info.reservation_id} for k8s cluster extension.")
        else:
            node_ids = [node.node_id for node in self.zos.nodes_finder.nodes_search(farm_name=farm_name)]
            trigger_cus = (pool.cus + cus) * 0.75
            trigger_sus = (pool.sus + sus) * 0.75
            pool_info = self.zos.pools.extend(pool_id, cus, sus, node_ids=node_ids)
            self.vdc_deployer.info(
                f"using pool {pool_id} extension reservation: {pool_info.reservation_id} for k8s cluster extension."
            )

        self.zos.billing.payout_farmers(self.wallet, pool_info)
        success = self.vdc_deployer.wait_pool_payment(pool_id, trigger_cus=trigger_cus, trigger_sus=trigger_sus)
        if not success:
            raise j.exceptions.Runtime(f"Pool {pool_info.reservation_id} resource reservation timedout")

        return pool_id

    def extend_cluster(self, farm_name, master_ip, k8s_flavor, cluster_secret, ssh_keys, no_nodes=1, duration=None):
        """
        search for a pool in the same farm and extend it or create a new one with the required capacity
        """
        old_node_ids = []
        for k8s_node in self.vdc_instance.kubernetes:
            old_node_ids.append(k8s_node.node_id)
        cc = CapacityChecker(farm_name)
        cc.exclude_nodes(*old_node_ids)

        for _ in range(no_nodes):
            if not cc.add_query(**K8S_SIZES[k8s_flavor]):
                raise j.exceptions.Validation(
                    f"not enough capacity in farm {farm_name} for {no_nodes} k8s nodes of flavor {k8s_flavor}"
                )

        duration = duration or self.vdc_instance.expiration.timestamp() - j.data.time.utcnow().timestamp
        if duration <= 0:
            raise j.exceptions.Validation(f"invalid duration {duration}")
        pool_id = self._preprare_extension_pool(farm_name, k8s_flavor, no_nodes, duration)
        scheduler = Scheduler(pool_id=pool_id)
        scheduler.exclude_nodes(*old_node_ids)
        network_view = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        nodes_generator = scheduler.nodes_by_capacity(**K8S_SIZES[k8s_flavor])
        solution_uuid = uuid.uuid4().hex
        wids = self._add_workers(
            pool_id,
            nodes_generator,
            k8s_flavor,
            cluster_secret,
            ssh_keys,
            solution_uuid,  # use differnet uuid than
            network_view,
            master_ip,
            no_nodes,
        )
        if not wids:
            self.vdc_deployer.error(f"failed to extend k8s cluster with {no_nodes} nodes of flavor {k8s_flavor}")
            j.sals.reservation_chatflow.solutions.cancel_solution_by_uuid(solution_uuid)
        return wids

    def _deploy_master(
        self, pool_id, nodes_generator, k8s_flavor, cluster_secret, ssh_keys, solution_uuid, network_view
    ):
        master_ip = None
        # deploy_master
        while not master_ip:
            try:
                try:
                    master_node = next(nodes_generator)
                except StopIteration:
                    return
                self.vdc_deployer.info(f"deploying kubernetes master on node {master_node.node_id}")
                # add node to network
                try:
                    result = deployer.add_network_node(
                        self.vdc_name, master_node, pool_id, network_view, self.bot, self.identity.instance_name
                    )
                    if result:
                        for wid in result["ids"]:
                            success = deployer.wait_workload(
                                wid, self.bot, 3, identity_name=self.identity.instance_name
                            )
                            if not success:
                                self.vdc_deployer.error(f"failed to deploy network for kubernetes master wid: {wid}")
                                raise DeploymentFailed
                except DeploymentFailed:
                    self.vdc_deployer.error(
                        f"failed to deploy network for kubernetes master on node {master_node.node_id}"
                    )
                    continue
            except IndexError:
                self.vdc_deployer.error("all tries to deploy k8s master node have failed")
                raise j.exceptions.Runtime("all tries to deploy k8s master node have failed")

            # deploy master
            network_view = network_view.copy()
            ip_address = network_view.get_free_ip(master_node)
            self.vdc_deployer.info(f"kubernetes master ip: {ip_address}")
            wid = deployer.deploy_kubernetes_master(
                pool_id,
                master_node.node_id,
                network_view.name,
                cluster_secret,
                ssh_keys,
                ip_address,
                size=k8s_flavor.value,
                secret=cluster_secret,
                identity_name=self.identity.instance_name,
                form_info={"chatflow": "kubernetes"},
                name=self.vdc_name,
                solution_uuid=solution_uuid,
                description=self.vdc_deployer.description,
            )
            self.vdc_deployer.info(f"kubernetes master wid: {wid}")
            try:
                success = deployer.wait_workload(wid, self.bot, identity_name=self.identity.instance_name)
                if not success:
                    raise DeploymentFailed()
                master_ip = ip_address
                return master_ip
            except DeploymentFailed:
                self.vdc_deployer.error(f"failed to deploy kubernetes master wid: {wid}")
                continue

    def _add_nodes_to_network(self, pool_id, nodes_generator, wids, no_nodes, network_view):
        deployment_nodes = []
        self.vdc_deployer.info(f"adding nodes to network. no_nodes: {no_nodes}, wids: {wids}")
        for node in nodes_generator:
            self.vdc_deployer.info(f"node {node.node_id} selected")
            deployment_nodes.append(node)
            if len(deployment_nodes) < no_nodes - len(wids):
                continue
            self.vdc_deployer.info(f"adding nodes {[node.node_id for node in deployment_nodes]} to network")
            # add nodes to network
            network_view = network_view.copy()
            result = []
            try:
                network_result = deployer.add_multiple_network_nodes(
                    self.vdc_name,
                    [node.node_id for node in deployment_nodes],
                    [pool_id] * len(deployment_nodes),
                    network_view,
                    self.bot,
                    self.identity.instance_name,
                )
                self.vdc_deployer.info(f"network update result: {network_result}")

                if network_result:
                    result += network_result["ids"]
                for wid in result:
                    try:
                        success = deployer.wait_workload(wid, self.bot, 5, identity_name=self.identity.instance_name)
                        if not success:
                            raise DeploymentFailed()
                    except DeploymentFailed:
                        # for failed network deployments
                        workload = self.zos.workloads.get(wid)
                        self.vdc_deployer.error(f"failed to add node {workload.info.node_id} to network. wid: {wid}")
                        success_nodes = []
                        for d_node in deployment_nodes:
                            if d_node.node_id == workload.info.node_id:
                                continue
                            success_nodes.append(node)
                        deployment_nodes = success_nodes
            except DeploymentFailed as e:
                # for dry run exceptions
                if e.wid:
                    workload = self.zos.workloads.get(e.wid)
                    self.vdc_deployer.error(f"failed to add node {workload.info.node_id} to network. wid: {e.wid}")
                    success_nodes = []
                    for d_node in deployment_nodes:
                        if d_node.node_id == workload.info.node_id:
                            continue
                        success_nodes.append(node)
                    deployment_nodes = success_nodes
                else:
                    self.vdc_deployer.error(f"network deployment failed on multiple nodes due to error {str(e)}")
                    deployment_nodes = []
                continue
            if len(deployment_nodes) == no_nodes:
                self.vdc_deployer.info("required nodes added to network successfully")
                return deployment_nodes

    def _add_workers(
        self,
        pool_id,
        nodes_generator,
        k8s_flavor,
        cluster_secret,
        ssh_keys,
        solution_uuid,
        network_view,
        master_ip,
        no_nodes,
    ):
        # deploy workers
        wids = []
        while True:
            result = []
            deployment_nodes = self._add_nodes_to_network(pool_id, nodes_generator, wids, no_nodes, network_view)
            if not deployment_nodes:
                self.vdc_deployer.error("no available nodes to deploy kubernetes workers")
                return
            self.vdc_deployer.info(
                f"deploying kubernetes workers on nodes {[node.node_id for node in deployment_nodes]}"
            )
            network_view = network_view.copy()
            # deploy workers
            for node in deployment_nodes:
                self.vdc_deployer.info(f"deploying kubernetes worker on node {node.node_id}")
                ip_address = network_view.get_free_ip(node)
                self.vdc_deployer.info(f"kubernetes worker ip address: {ip_address}")
                result.append(
                    deployer.deploy_kubernetes_worker(
                        pool_id,
                        node.node_id,
                        network_view.name,
                        cluster_secret,
                        ssh_keys,
                        ip_address,
                        master_ip,
                        size=k8s_flavor.value,
                        secret=cluster_secret,
                        identity_name=self.identity.instance_name,
                        form_info={"chatflow": "kubernetes"},
                        name=self.vdc_name,
                        solution_uuid=solution_uuid,
                        description=self.vdc_deployer.description,
                    )
                )
            for wid in result:
                try:
                    success = deployer.wait_workload(wid, self.bot, identity_name=self.identity.instance_name)
                    if not success:
                        raise DeploymentFailed()
                    wids.append(wid)
                    self.vdc_deployer.info(f"kubernetes worker deployed sucessfully wid: {wid}")
                except DeploymentFailed:
                    self.vdc_deployer.error(f"failed to deploy kubernetes worker wid: {wid}")
                    pass

            self.vdc_deployer.info(f"successful kubernetes workers ids: {wids}")
            if len(wids) == no_nodes:
                self.vdc_deployer.info(f"all workers deployed successfully")
                return wids

    def download_kube_config(self, master_ip):
        """
        Args:
            master ip: public ip address of kubernetes master
        """
        ssh_client = j.clients.sshclient.get(uuid.uuid4().hex, user="rancher", host=master_ip, sshkey=self.vdc_name)
        rc, out, err = ssh_client.run("cat /etc/rancher/k3s/k3s.yaml")
        if rc:
            j.logger.error(f"couldn't read k3s config for vdc {self.vdc_name}")
            j.tools.alerthandler.alert_raise(
                "vdc", f"couldn't read k3s config for vdc {self.vdc_name} rc: {rc}, out: {out}, err: {err}"
            )
            raise j.exceptions.Runtime(f"Couldn't download kube config for vdc: {self.vdc_name}.")
        j.clients.sshclient.delete(ssh_client.instance_name)
        j.sals.fs.mkdirs(f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}")
        j.sals.fs.write_file(f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}/{self.vdc_name}.yaml", out)
        return out
