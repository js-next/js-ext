import math
import uuid
import re
import copy
from jumpscale.loader import j
from jumpscale.sals.reservation_chatflow import deployer
from jumpscale.sals.reservation_chatflow.deployer import DeploymentFailed

from .base_component import VDCBaseComponent
from .scheduler import CapacityChecker, Scheduler
from .size import *
from jumpscale.clients.explorer.models import K8s, NextAction, WorkloadType
from jumpscale.sals.vdc.kubernetes_auto_extend import KubernetesMonitor
from jumpscale.sals.kubernetes import Manager
import gevent
import ipaddress
from .scheduler import GlobalScheduler

import random
import datetime

ETCD_FLIST = "https://hub.grid.tf/ahmed_hanafy_1/ahmedhanafy725-etcd-latest.flist"
VDC_SYSTEM_NAMESPACES = ["k3os-system", "kube-public", "kube-system", "velero"]


class VDCKubernetesDeployer(VDCBaseComponent):
    def __init__(self, *args, **kwrags) -> None:
        super().__init__(*args, **kwrags)

    def _preprare_extension_pool(self, farm_name, k8s_flavor, no_nodes, duration, public_ip=False, no_extend=False):
        """
        returns pool id after extension with enough cloud units
        duration in seconds
        """
        self.vdc_deployer.info(
            f"Preperaring pool for kubernetes cluster extension on farm {farm_name}, flavor: {k8s_flavor}, no_nodes: {no_nodes}, duration: {duration}, public_ip: {public_ip},vdc uuid: {self.vdc_uuid}"
        )
        k8s = K8s()
        k8s.size = k8s_flavor.value
        cloud_units = k8s.resource_units().cloud_units()
        cus = int(cloud_units.cu * duration * no_nodes)
        sus = int(cloud_units.su * duration * no_nodes)
        ipv4us = 0
        if public_ip:
            ipv4us = int(duration)

        farm = self.explorer.farms.get(farm_name=farm_name)
        pool_id = None
        self.vdc_deployer.info(f"kubernetes cluster extension: searching for existing pool on farm {farm_name}")
        for pool in self.zos.pools.list():
            farm_id = deployer.get_pool_farm_id(pool.pool_id, pool, self.identity.instance_name)
            if farm_id == farm.id:
                pool_id = pool.pool_id
                break

        if not pool_id:
            pool_info = self.vdc_deployer._retry_call(
                self.zos.pools.create,
                args=[math.ceil(cus), math.ceil(sus), ipv4us, farm_name, ["TFT"], j.core.identity.me],
            )
            pool_id = pool_info.reservation_id
            self.vdc_deployer.info(f"Kubernetes cluster extension: creating a new pool {pool_id}")
            self.vdc_deployer.info(f"New pool {pool_info.reservation_id} for kubernetes cluster extension.")
        elif no_extend:
            return pool_id
        else:
            self.vdc_deployer.info(f"Kubernetes cluster extension: found pool {pool_id}")
            node_ids = [node.node_id for node in self.zos.nodes_finder.nodes_search(farm_name=farm_name)]
            pool_info = self.vdc_deployer._retry_call(
                self.zos.pools.extend, args=[pool_id, cus, sus, ipv4us], kwargs={"node_ids": node_ids}
            )
            self.vdc_deployer.info(
                f"Using pool {pool_id} extension reservation: {pool_info.reservation_id} for kubernetes cluster extension."
            )

        self.vdc_deployer.pay(pool_info)

        success = self.vdc_deployer.wait_pool_payment(pool_info.reservation_id)
        if not success:
            raise j.exceptions.Runtime(f"Pool {pool_info.reservation_id} resource reservation timedout")

        return pool_id

    def list_node_releases(self, wid, exclude_namespaces: list = None, exclude_system_namespaces=True):
        """List all releases on/partially on kubernetes node using wid of the node

        Args:
            wid (int): Kubernetes node workload id
            exclude_namespaces (list, optional): list of namespaces to exclude. Defaults to None.
            exclude_system_namespaces (bool, optional): Whether to exclude system namespaces or Not. Defaults to True.

        Returns:
            list[str]: list of releases names
        """
        namespaces_to_exclude = []
        if exclude_namespaces:
            namespaces_to_exclude.extend(exclude_namespaces)
        if exclude_system_namespaces:
            namespaces_to_exclude.extend(VDC_SYSTEM_NAMESPACES)

        kube_manager = Manager()
        node_name = self.get_node_name(wid)
        out = kube_manager.execute_native_cmd(
            f"kubectl get pods -A -o json --sort-by='.metadata.namespace' --field-selector spec.nodeName={node_name}"
        )
        all_pods = j.data.serializers.json.loads(out)["items"]
        releases = set()
        for pod in all_pods:
            # Exclude system pods and pods related to deleted releases, as it is not needed
            if pod["metadata"]["namespace"] in namespaces_to_exclude:
                continue
            releases.add(pod["metadata"]["namespace"])
        return list(releases)

    # TODO: to be used and modified when we implement our cloud volumes
    def check_solutions_rescheduled_availability(self, wid):
        """Check for availability of rescheduling solutions deployed on one kubernetes node to another node

        Args:
            wid (int): workload id for the kubernetes node

        Returns:
            bool: Check if drain is available without deleting any release or not
            list: List of the releases that will be affected (deleted) if drain is not available
        """
        kube_manager = Manager()
        kube_monitor = KubernetesMonitor(self.vdc_instance)
        node_name_to_delete = [self.get_node_name(wid)]
        remaining_nodes_reservations = kube_monitor.fetch_resource_reservations(exclude_nodes=node_name_to_delete)

        # Get pods on the node we want to delete
        out = kube_manager.execute_native_cmd(
            f"kubectl get pods -A -o json --sort-by='.metadata.namespace' --field-selector spec.nodeName={node_name_to_delete[0]}"
        )
        all_pods_to_redeploy = j.data.serializers.json.loads(out)
        releases_to_delete = []
        previous_release = ""
        temp_nodes_reservations = kube_monitor.fetch_resource_reservations(exclude_nodes=node_name_to_delete)
        # Check if every pod can be deployed again in another node
        for pod in all_pods_to_redeploy["items"]:
            # Exclude system pods and pods related to deleted releases, as it is not needed
            if (
                pod["metadata"]["namespace"] in VDC_SYSTEM_NAMESPACES
                or pod["metadata"]["namespace"] in releases_to_delete
            ):
                continue
            # Check if it is new namespace, so we can calculate the remaining resources more accurate
            if pod["metadata"]["namespace"] != previous_release:
                if previous_release not in releases_to_delete:
                    # Update nodes resources with all need resources from the previous release
                    remaining_nodes_reservations = copy.deepcopy(temp_nodes_reservations)
                else:
                    # Reset temp_nodes_reservations with the accurate remaining resources in the nodes
                    temp_nodes_reservations = copy.deepcopy(remaining_nodes_reservations)

            # Get pod resources
            cpu = memory = 0
            can_deploy = False
            for cont in pod["spec"]["containers"]:
                cont_requests = cont["resources"].get("requests", {})
                cpu_str = cont_requests.get("cpu", "0m")
                if not cpu_str.endswith("m"):
                    cpu += float(cpu_str) * 1000
                else:
                    cpu += float(cpu_str.split("m")[0])
                p = re.search(r"^([0-9]*)(.*)$", cont_requests.get("memory", "0Gi"))
                memory = float(p.group(1))
                memory_unit = p.group(2)
                if memory_unit == "Gi":
                    memory *= 1024

            # Check if it can be deployed in another node
            for node in temp_nodes_reservations:
                if node.has_enough_resources(cpu=cpu, memory=memory):
                    can_deploy = True
                    node.update(cpu=cpu, memory=memory)
                    break

            if not can_deploy:
                releases_to_delete.append(pod["metadata"]["namespace"])
                j.logger.warning(f"Pod: {pod['metadata']['name']} can't be redeployed on any other node")

            previous_release = pod["metadata"]["namespace"]

        # Return bool for check, and pods that can not redeployed again
        return len(releases_to_delete) == 0, releases_to_delete

    def extend_cluster(
        self,
        farm_name,
        master_ip,
        k8s_flavor,
        cluster_secret,
        ssh_keys,
        no_nodes=1,
        duration=None,
        public_ip=False,
        solution_uuid=None,
        external=True,
        nodes_ids=None,
        no_extend_pool=False,
    ):
        """
        search for a pool in the same farm and extend it or create a new one with the required capacity
        """
        old_node_ids = []
        for k8s_node in self.vdc_instance.kubernetes:
            old_node_ids.append(k8s_node.node_id)
        cc = CapacityChecker(farm_name)
        cc.exclude_nodes(*old_node_ids)

        for _ in range(no_nodes):
            if not cc.add_query(**VDC_SIZE.K8S_SIZES[k8s_flavor]):
                raise j.exceptions.Validation(
                    f"Not enough capacity in farm {farm_name} for {no_nodes} kubernetes nodes of flavor {k8s_flavor}"
                )

        duration = (
            duration * 60 * 60 * 24
            if duration
            else self.vdc_instance.expiration_date.timestamp() - j.data.time.utcnow().timestamp
        )
        if duration <= 0:
            raise j.exceptions.Validation(f"invalid duration {duration}")
        scheduler = Scheduler(farm_name=farm_name)
        scheduler.exclude_nodes(*old_node_ids)
        nodes_generator = scheduler.nodes_by_capacity(**VDC_SIZE.K8S_SIZES[k8s_flavor], public_ip=public_ip)
        if nodes_ids:
            nodes_generator = list(nodes_generator)
            nodes_generator_ids = [node.node_id for node in nodes_generator]
            unavailable_nodes_ids = set(nodes_ids) - set(nodes_generator_ids)
            if unavailable_nodes_ids:
                raise j.exceptions.Validation(
                    f"Some nodes: {unavailable_nodes_ids} are not in farm: {farm_name} or don't have capacity"
                )
            nodes_generator = [node for node in nodes_generator if node.node_id in nodes_ids]
        pool_id = self._preprare_extension_pool(
            farm_name, k8s_flavor, no_nodes, duration, public_ip, no_extend=no_extend_pool
        )
        network_view = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        solution_uuid = solution_uuid or uuid.uuid4().hex
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
            public_ip,
            external,
        )
        if not wids:
            self.vdc_deployer.error(
                f"Failed to extend kubernetes cluster with {no_nodes} nodes of flavor {k8s_flavor}, vdc uuid {self.vdc_uuid}"
            )
            j.sals.reservation_chatflow.solutions.cancel_solution_by_uuid(solution_uuid)
            raise j.exceptions.Runtime(
                f"failed to extend kubernetes cluster with {no_nodes} nodes of flavor {k8s_flavor}, vdc uuid {self.vdc_uuid}"
            )
        return wids

    def deploy_master(
        self,
        pool_id,
        scheduler,
        k8s_flavor,
        cluster_secret,
        ssh_keys,
        solution_uuid,
        network_view,
        datastore_endpoint="",
        network_subnet="",
        private_ip="",
        public_ip=None,
    ):
        master_ip = None
        # deploy_master
        k8s_resources_dict = VDC_SIZE.K8S_SIZES[k8s_flavor]
        nodes_generator = scheduler.nodes_by_capacity(**k8s_resources_dict, pool_id=pool_id, public_ip=True)
        while not master_ip:
            try:
                try:
                    master_node = next(nodes_generator)
                except StopIteration:
                    return
                self.vdc_deployer.info(
                    f"Deploying kubernetes master on node {master_node.node_id} with datastore: {datastore_endpoint}"
                )
                # add node to network
                try:
                    result = deployer.add_network_node(
                        self.vdc_name,
                        master_node,
                        pool_id,
                        network_view,
                        self.bot,
                        self.identity.instance_name,
                        subnet=network_subnet,
                    )
                    if result:
                        for wid in result["ids"]:
                            success = deployer.wait_workload(
                                wid, self.bot, 3, identity_name=self.identity.instance_name, cancel_by_uuid=False
                            )
                            if not success:
                                self.vdc_deployer.error(f"Failed to deploy network for kubernetes master wid: {wid}")
                                raise DeploymentFailed
                except DeploymentFailed:
                    self.vdc_deployer.error(
                        f"Failed to deploy network for kubernetes master on node {master_node.node_id}"
                    )
                    continue
            except IndexError:
                self.vdc_deployer.error("All attempts to deploy kubernetes master node have failed")
                raise j.exceptions.Runtime("All attempts to deploy kubernetes master node have failed")

            # reserve public_ip
            if public_ip:
                public_ip_wid = self.vdc_deployer.public_ip.get_specific_public_ip(
                    pool_id, master_node.node_id, public_ip, solution_uuid=solution_uuid
                )
            else:
                public_ip_wid = self.vdc_deployer.public_ip.get_public_ip(
                    pool_id, master_node.node_id, solution_uuid=solution_uuid
                )

            if not public_ip_wid:
                self.vdc_deployer.error(f"Failed to reserve public ip on node {master_node.node_id}")
                continue

            # deploy master
            if private_ip:
                private_ip_address = private_ip
            else:
                network_view = network_view.copy()
                private_ip_address = network_view.get_free_ip(master_node)
            self.vdc_deployer.info(f"Kubernetes master ip: {private_ip_address}")
            wid = deployer.deploy_kubernetes_master(
                pool_id,
                master_node.node_id,
                network_view.name,
                cluster_secret,
                ssh_keys,
                private_ip_address,
                size=k8s_flavor.value,
                identity_name=self.identity.instance_name,
                # form_info={"chatflow": "kubernetes"},
                # name=self.vdc_name,
                secret=cluster_secret,
                solution_uuid=solution_uuid,
                description=self.vdc_deployer.description,
                public_ip_wid=public_ip_wid,
                datastore_endpoint=datastore_endpoint,
                disable_default_ingress=False,
            )
            self.vdc_deployer.info(f"Kubernetes master wid: {wid}")
            try:
                success = deployer.wait_workload(
                    wid, self.bot, identity_name=self.identity.instance_name, cancel_by_uuid=False
                )
                if not success:
                    raise DeploymentFailed()
                master_ip = private_ip_address
                return master_ip
            except DeploymentFailed:
                self.zos.workloads.decomission(public_ip_wid)
                self.vdc_deployer.error(f"Failed to deploy kubernetes master wid: {wid}")
                continue
        self.vdc_deployer.error(f"All attempts to deploy kubernetes master have failed")

    def _add_nodes_to_network(self, pool_id, nodes_generator, wids, no_nodes, network_view):
        deployment_nodes = []
        self.vdc_deployer.info(f"Adding nodes to network. no_nodes: {no_nodes}, wids: {wids}")
        for node in nodes_generator:
            self.vdc_deployer.info(f"node {node.node_id} selected")
            deployment_nodes.append(node)
            if len(deployment_nodes) < no_nodes - len(wids):
                continue
            self.vdc_deployer.info(f"Adding nodes {[node.node_id for node in deployment_nodes]} to network")
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
                self.vdc_deployer.info(f"Network update result: {network_result}")

                if network_result:
                    result += network_result["ids"]
                for wid in result:
                    try:
                        success = deployer.wait_workload(
                            wid, self.bot, 5, identity_name=self.identity.instance_name, cancel_by_uuid=False
                        )
                        if not success:
                            raise DeploymentFailed()
                    except DeploymentFailed:
                        # for failed network deployments
                        workload = self.zos.workloads.get(wid)
                        self.vdc_deployer.error(f"Failed to add node {workload.info.node_id} to network. wid: {wid}")
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
                    self.vdc_deployer.error(f"Failed to add node {workload.info.node_id} to network. wid: {e.wid}")
                    success_nodes = []
                    for d_node in deployment_nodes:
                        if d_node.node_id == workload.info.node_id:
                            continue
                        success_nodes.append(node)
                    deployment_nodes = success_nodes
                else:
                    self.vdc_deployer.error(f"Network deployment failed on multiple nodes due to error {str(e)}")
                    deployment_nodes = []
                continue
            if len(deployment_nodes) == no_nodes:
                self.vdc_deployer.info("Required nodes added to network successfully")
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
        public_ip=False,
        external=True,
    ):
        # deploy workers
        wids = []
        while True:
            result = []
            public_wids = []
            deployment_nodes = self._add_nodes_to_network(pool_id, nodes_generator, wids, no_nodes, network_view)
            if not deployment_nodes:
                self.vdc_deployer.error("No available nodes to deploy kubernetes workers")
                return
            self.vdc_deployer.info(
                f"Deploying kubernetes workers on nodes {[node.node_id for node in deployment_nodes]}"
            )
            network_view = network_view.copy()
            # deploy workers
            for node in deployment_nodes:
                if public_ip:
                    public_ip_wid = self.vdc_deployer.public_ip.get_public_ip(pool_id, node.node_id, solution_uuid)
                    if not public_ip_wid:
                        self.vdc_deployer.error(f"Failed to deploy reserve public ip on node {node.node_id}")
                        continue
                else:
                    public_ip_wid = 0
                self.vdc_deployer.info(f"Deploying kubernetes worker on node {node.node_id}")
                ip_address = network_view.get_free_ip(node)
                self.vdc_deployer.info(f"Kubernetes worker ip address: {ip_address}")
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
                        # form_info={"chatflow": "kubernetes"},
                        # name=self.vdc_name,
                        solution_uuid=solution_uuid,
                        description=self.vdc_deployer.description,
                        public_ip_wid=public_ip_wid,
                        external=external,
                    )
                )
                public_wids.append(public_ip_wid)
            for idx, wid in enumerate(result):
                try:
                    success = deployer.wait_workload(
                        wid, self.bot, identity_name=self.identity.instance_name, cancel_by_uuid=False
                    )
                    if not success:
                        raise DeploymentFailed()
                    wids.append(wid)
                    self.vdc_deployer.info(f"Kubernetes worker deployed successfully wid: {wid}")
                except DeploymentFailed:
                    if public_wids[idx]:
                        self.zos.workloads.decomission(public_wids[idx])
                    self.vdc_deployer.error(f"Failed to deploy kubernetes worker wid: {wid}")

            self.vdc_deployer.info(f"successful kubernetes workers ids: {wids}")
            if len(wids) == no_nodes:
                self.vdc_deployer.info(f"All workers deployed successfully")
                return wids
        self.vdc_deployer.error("All tries to deploy kubernetes workers have failed")

    def download_kube_config(self, master_ip):
        """
        Args:
            master ip: public ip address of kubernetes master
        """
        if not j.sals.nettools.wait_connection_test(master_ip, 6443, timeout=120):
            raise j.exceptions.Runtime(
                f"Couldn't download kube config for vdc: failed to wait for cluster init {self.vdc_name}."
            )
        if not j.sals.nettools.wait_connection_test(master_ip, 22, timeout=120):
            raise j.exceptions.Runtime(
                f"Couldn't download kube config for vdc: failed to wait for cluster ssh {self.vdc_name}."
            )
        client_name = self.vdc_deployer.ssh_key.instance_name
        ssh_client = j.clients.sshclient.get(client_name, user="rancher", host=master_ip, sshkey=client_name)
        rc, out, err = 1, "init", "init"
        retries = 12
        while rc and retries > 0:
            rc, out, err = ssh_client.sshclient.run("cat /etc/rancher/k3s/k3s.yaml", warn=True)
            retries -= 1
            gevent.sleep(2)
        if rc:
            j.logger.error(f"Couldn't read k3s config for VDC {self.vdc_name}")
            j.tools.alerthandler.alert_raise(
                "vdc",
                f"Couldn't read k3s config for VDC {self.vdc_name} rc: {rc}, out: {out}, err: {err}, vdc uuid: {self.vdc_uuid}",
            )
            raise j.exceptions.Runtime(f"Couldn't download kube config for vdc: {self.vdc_name}.")
        j.clients.sshclient.delete(ssh_client.instance_name)
        config_dict = j.data.serializers.yaml.loads(out)
        config_dict["clusters"][0]["cluster"]["server"] = f"https://{master_ip}:6443"
        out = j.data.serializers.yaml.dumps(config_dict)
        j.sals.fs.mkdirs(f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}")
        j.sals.fs.write_file(f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}/{self.vdc_name}.yaml", out)
        return out

    def get_node_name(self, wid):
        kube_monitor = KubernetesMonitor(self.vdc_instance)
        all_node_stats = kube_monitor.node_stats
        return [node for node in all_node_stats.keys() if all_node_stats[node]["wid"] == wid][0]

    def delete_worker(self, wid, is_ready=False):
        kube_manager = Manager()
        workloads_to_delete = []
        workload = self.zos.workloads.get(wid)
        node_name = self.get_node_name(wid)

        if not workload.master_ips:
            raise j.exceptions.Input("Can't delete controller node")
        if workload.info.next_action == NextAction.DEPLOY:
            workloads_to_delete.append(wid)
        if workload.public_ip:
            public_ip_workload = self.zos.workloads.get(workload.public_ip)
            if public_ip_workload.info.next_action == NextAction.DEPLOY:
                workloads_to_delete.append(public_ip_workload.id)
        if is_ready:
            # Drain node to safely delete it.
            kube_manager.execute_native_cmd(
                f"kubectl drain {node_name} --delete-local-data --ignore-daemonsets --force"
            )

        # Delete node to remove it from the cluster
        kube_manager.execute_native_cmd(f"kubectl delete nodes {node_name}")

        for wid in workloads_to_delete:
            self.zos.workloads.decomission(wid)
        return workloads_to_delete

    # TODO: better implementatiom
    def upgrade_traefik(self, version="9.20.1"):
        """
        Args:
            version: traefik chart helm version default: "9.20.1"
        Upgrades traefik chart installed on k3s to support different CAs
        """

        def is_traefik_installed(manager):
            releases = manager.list_deployed_releases()
            # TODO: List only using names
            for release in releases:
                if release.get("name") == "traefik":
                    return True, release.get("namespace")
            return False, ""

        def is_traefik_stuck(manager):
            # check if the release is stuck
            releases = manager.list_stuck_releases()
            for release in releases:
                if release.get("name") == "traefik":
                    return True, release.get("namespace")
            return False, ""

        def clean_traefik(manager):
            # wait until traefik chart is installed on the cluster then uninstall it
            checks = 12
            while checks > 0:
                res, ns = is_traefik_installed(manager)
                if res:
                    break
                gevent.sleep(5)
                checks -= 1
            else:  # no break
                res, ns = is_traefik_stuck(manager)
                if not res:
                    return
            manager.delete_deployed_release("traefik", ns)

        kubeconfig_path = f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}/{self.vdc_name}.yaml"
        k8s_client = j.sals.kubernetes.Manager(config_path=kubeconfig_path)
        k8s_client.add_helm_repo("traefik", "https://helm.traefik.io/traefik")
        k8s_client.update_repos()

        t = gevent.spawn(clean_traefik, k8s_client)
        t.join()

        # install traefik chart
        # TODO: better code for the values
        k8s_client.install_chart(
            "traefik",
            "traefik/traefik",
            "kube-system",
            version=version,
            chart_values_file=f"""<(echo -e '
additionalArguments:
  - "--certificatesresolvers.default.acme.tlschallenge"
  - "--certificatesresolvers.default.acme.email=dsafsdajfksdhfkjadsfoo@you.com"
  - "--certificatesresolvers.default.acme.storage=/data/acme.json"
  - "--certificatesresolvers.default.acme.caserver=https://acme-staging-v02.api.letsencrypt.org/directory"
  - "--certificatesresolvers.default.acme.httpchallenge.entrypoint=web"
  - "--certificatesresolvers.gridca.acme.tlschallenge"
  - "--certificatesresolvers.gridca.acme.email=dsafsdajfksdhfkjadsfoo@you.com"
  - "--certificatesresolvers.gridca.acme.storage=/data/acme1.json"
  - "--certificatesresolvers.gridca.acme.caserver=https://ca1.grid.tf"
  - "--certificatesresolvers.gridca.acme.httpchallenge.entrypoint=web"
  - "--certificatesresolvers.le.acme.tlschallenge"
  - "--certificatesresolvers.le.acme.email=dsafsdajfksdhfkjadsfoo@you.com"
  - "--certificatesresolvers.le.acme.storage=/data/acme2.json"
  - "--certificatesresolvers.le.acme.caserver=https://acme-v02.api.letsencrypt.org/directory"
  - "--certificatesresolvers.le.acme.httpchallenge.entrypoint=web"
ports:
  web:
    redirectTo: websecure
  websecure:
    tls:
      enabled: true')""",
        )

    def add_traefik_entrypoint(self, entrypoint_name, port, expose=True, protocol="TCP"):
        """
        Add a new entrypoint to traefik or override an existing one
        """
        if not str(port).isnumeric():
            raise ValueError("Port must be numeric")
        kubeconfig_path = f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}/{self.vdc_name}.yaml"
        k8s_client = j.sals.kubernetes.Manager(config_path=kubeconfig_path)
        k8s_client.add_helm_repo("traefik", "https://helm.traefik.io/traefik")
        k8s_client.update_repos()
        config_str = k8s_client.get_helm_chart_user_values("traefik", "kube-system")
        config_json = j.data.serializers.json.loads(config_str)
        config_json["ports"][entrypoint_name] = {
            "port": port,
            "exposedPort": port,
            "expose": expose,
            "protocol": protocol,
        }
        config_yaml = j.data.serializers.yaml.dumps(config_json)
        k8s_client.upgrade_release("traefik", "traefik/traefik", "kube-system", config_yaml)

    def deploy_external_etcd(self, farm_name, no_nodes=ETCD_CLUSTER_SIZE, solution_uuid=None):
        network_view = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        pool_id, _ = self.vdc_deployer.get_pool_id_and_reservation_id(farm_name)
        scheduler = Scheduler(pool_id=pool_id)
        nodes_generator = scheduler.nodes_by_capacity(cru=ETCD_CPU, sru=ETCD_DISK / 1024, mru=ETCD_MEMORY / 1024)
        solution_uuid = solution_uuid or uuid.uuid4().hex
        while True:
            deployment_nodes = self._add_nodes_to_network(pool_id, nodes_generator, [], no_nodes, network_view)
            if not deployment_nodes:
                self.vdc_deployer.error("no available nodes to deploy etcd cluster")
                return
            self.vdc_deployer.info(f"deploying etcd cluster on nodes {[node.node_id for node in deployment_nodes]}")

            network_view = network_view.copy()
            ip_addresses = []
            node_ids = []
            etcd_cluster = ""

            for idx, node in enumerate(deployment_nodes):
                address = network_view.get_free_ip(node)
                ip_addresses.append(address)
                etcd_cluster += f"etcd_{idx+1}=http://{address}:2380,"
                node_ids.append(node.node_id)

            secret_env = None
            # etcd_backup_config = j.core.config.get("VDC_S3_CONFIG", {})
            # restic_url = etcd_backup_config.get("S3_URL", "")
            # restic_bucket = etcd_backup_config.get("S3_BUCKET", "")
            # restic_ak = etcd_backup_config.get("S3_AK", "")
            # restic_sk = etcd_backup_config.get("S3_SK", "")
            # if all([self.vdc_deployer.restore, restic_url, restic_bucket, restic_ak, restic_sk]):
            #     secret_env = {
            #         "RESTIC_REPOSITORY": f"s3:{restic_url}/{restic_bucket}/{self.vdc_instance.owner_tname}/{self.vdc_instance.vdc_name}",
            #         "AWS_ACCESS_KEY_ID": restic_ak,
            #         "AWS_SECRET_ACCESS_KEY": restic_sk,
            #         "RESTIC_PASSWORD": self.vdc_deployer.password_hash,
            #     }

            explorer = None
            if "test" in j.core.identity.me.explorer_url:
                explorer = "test"
            elif "dev" in j.core.identity.me.explorer_url:
                explorer = "dev"
            else:
                explorer = "main"
            log_config = j.core.config.get("VDC_LOG_CONFIG", {})
            if log_config:
                log_config["channel_name"] = f"{self.vdc_instance.instance_name}_{explorer}"
            pool_ids = [pool_id for i in range(no_nodes)]
            wids = deployer.deploy_etcd_containers(
                pool_ids,
                node_ids,
                network_view.name,
                ip_addresses,
                etcd_cluster,
                ETCD_FLIST,
                ETCD_CPU,
                ETCD_MEMORY,
                ETCD_DISK,
                entrypoint="",
                ssh_key=self.vdc_deployer.ssh_key.public_key.strip(),
                identity_name=self.identity.instance_name,
                solution_uuid=solution_uuid,
                description=self.vdc_deployer.description,
                secret_env=secret_env,
                log_config=log_config,
            )
            try:
                for wid in wids:
                    success = deployer.wait_workload(
                        wid, self.bot, identity_name=self.identity.instance_name, cancel_by_uuid=False
                    )
                    if not success:
                        self.vdc_deployer.error(f"etcd cluster workload: {wid} failed to deploy")
                        raise DeploymentFailed()
            except DeploymentFailed:
                for wid in wids:
                    self.zos.workloads.decomission(wid)
                continue
            return ip_addresses

    def add_traefik_entrypoints(self, entrypoints):
        """
        Add a new entrypoint to traefik or override an existing one

        Args:
            entrypoints (dict): contains a mapping from the entrypoint name to its spec
                spec:
                    port (str|int): The entrypoint port
                    expose (bool): Optional, whether to expose the port to outside the cluster, default: True
                    protocol (str): Optional, TCP|UDP, default: TCP
        """

        kubeconfig_path = f"{j.core.dirs.CFGDIR}/vdc/kube/{self.vdc_deployer.tname}/{self.vdc_name}.yaml"
        k8s_client = j.sals.kubernetes.Manager(config_path=kubeconfig_path)
        k8s_client.add_helm_repo("traefik", "https://helm.traefik.io/traefik")
        k8s_client.update_repos()
        config_str = k8s_client.get_helm_chart_user_values("traefik", "kube-system")
        config_json = j.data.serializers.json.loads(config_str)
        for entrypoint_name, entrypoint in entrypoints.items():
            port = entrypoint.get("port")
            if port is None or not str(port).isnumeric():
                raise ValueError("Port is required and it must be numeric in the entrypoint definition")
            expose = entrypoint.get("expose", True)
            protocol = entrypoint.get("protocol", "TCP")
            config_json["ports"][entrypoint_name] = {
                "port": port,
                "exposedPort": port,
                "expose": expose,
                "protocol": protocol,
            }
        config_yaml = j.data.serializers.yaml.dumps(config_json)
        k8s_client.upgrade_release("traefik", "traefik/traefik", "kube-system", config_yaml)

    def _get_latest_master_workload(self):
        latest_workload = None
        workloads = self.zos.workloads.list_workloads(self.vdc_instance.identity_tid)
        for workload in workloads:
            if workload.info.workload_type == WorkloadType.Kubernetes and not workload.master_ips:
                latest_workload = workload
        return latest_workload

    def _ip_in_network(self, ip, network):
        ip_addr = ipaddress.ip_address(ip)
        net = ipaddress.ip_network(network)
        return ip_addr in net

    def redeploy_master(self, old_master_workload=None):
        nv = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        if not old_master_workload:
            old_master_workload = self._get_latest_master_workload()
            if not old_master_workload:
                self.vdc_deployer.error("Couldn't find old master workload")
                return

        # delete old master in case of next action is deploy
        if old_master_workload.info.next_action == NextAction.DEPLOY:
            self.vdc_deployer.info(f"Deleting old master workload {old_master_workload.id}")
            self.zos.workloads.decomission(old_master_workload.id)
            deployer.wait_workload_deletion(old_master_workload.id)

        # deleting network old network
        # old_network_workload = None
        # workloads = self.zos.workloads.list_workloads(self.vdc_instance.identity_tid)
        # for workload in workloads:
        #     if workload.info.workload_type == WorkloadType.Network_resource and self._ip_in_network(
        #         old_master_workload.ipaddress, workload.iprange
        #     ):
        #         old_network_workload = workload
        #         break

        # self.vdc_deployer.info(f"Deleting old network on node {old_network_workload.info.node_id}")
        # nv.delete_node(old_network_workload.info.node_id)

        master_size = VDC_SIZE.VDC_FLAVORS[self.vdc_deployer.flavor]["k8s"]["controller_size"]
        pub_keys = [self.vdc_deployer.ssh_key.public_key.strip()]
        gs = GlobalScheduler()  # need to used nodes
        self.vdc_instance.load_info()
        endpoints = ",".join([f"http://{etcd.ip_address}:2379" for etcd in self.vdc_instance.etcd])
        self.vdc_deployer.info("Deploying new master")
        public_ip_workload = self.zos.workloads.get(old_master_workload.public_ip)
        self.deploy_master(
            old_master_workload.info.pool_id,
            gs,
            master_size,
            self.vdc_instance.get_password(),
            pub_keys,
            self.vdc_uuid,
            nv,
            endpoints,
            public_ip=public_ip_workload.ipaddress,
        )
        return True
