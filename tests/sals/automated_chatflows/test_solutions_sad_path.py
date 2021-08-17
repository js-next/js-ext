import pytest
from jumpscale.loader import j
from redis import Redis
from solutions_automation import deployer
from tests.sals.automated_chatflows.chatflows_base import ChatflowsBase
from parameterized import parameterized_class
from gevent import sleep
from unittest import TestCase
from parameterized import parameterized


@pytest.mark.integration
class TFGridSolutionChatflowsSadPath(ChatflowsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Accept admin T&C for testing identity.
        cls.accept_terms_conditions(type_="admin")

        # Create Network
        cls.network_name = cls.random_name()
        cls.wg_conf_paths = [f"/tmp/{cls.random_name()}.conf"]
        network = deployer.create_network(solution_name=cls.network_name)
        j.sals.fs.write_file(cls.wg_conf_paths[-1], network.wgconf)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {cls.wg_conf_paths[-1]}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")
        sleep(5)
        _, out, err = j.sals.process.execute("sudo wg")
        TestCase().assertIn("latest handshake", out, f"out: {out}, err: {err}")

        # Prepare ssh
        cls.ssh_client_name = cls.random_name()
        if not j.sals.fs.exists("/tmp/.ssh"):
            j.core.executors.run_local(
                'mkdir /tmp/.ssh && ssh-keygen -t rsa -f /tmp/.ssh/id_rsa -q -N "" '
            )  # TODO: Fix me use ssh generate method
        cls.ssh_cl = j.clients.sshkey.get(cls.ssh_client_name)
        cls.ssh_cl.private_key_path = "/tmp/.ssh/id_rsa"
        cls.ssh_cl.load_from_file_system()
        cls.ssh_cl.save()
        cls.solution_uuid = ""

        # create a pool
        cls.pool_name = cls.random_name()
        farm = cls.get_farm_name().capitalize()
        pool = deployer.create_pool(
            solution_name=cls.pool_name,
            farm=farm,
            cu=1,
            su=1,
            time_unit="Day",
            time_to_live=1,
            wallet_name="demos_wallet",
        )
        cls.pool_id = pool.pool_data.reservation_id

    @classmethod
    def tearDownClass(cls):
        for path in cls.wg_conf_paths:
            j.sals.process.execute(f"sudo wg-quick down {path}")
            j.sals.fs.rmtree(path=path)
        j.sals.fs.rmtree(path="/tmp/.ssh")
        j.clients.sshkey.delete(cls.ssh_client_name)

        # delete network
        network_view = j.sals.reservation_chatflow.deployer.get_network_view(cls.network_name)
        wids = [w.id for w in network_view.network_workloads]
        j.sals.zos.get().workloads.decomission(workload_id=wids[0])

        # Remove userEntry for accepting T&C
        cls.user_factory.delete(cls.user_entry_name)
        super().tearDownClass()

    def tearDown(self):
        if self.solution_uuid:
            j.sals.reservation_chatflow.solutions.cancel_solution_by_uuid(self.solution_uuid)
        j.clients.sshclient.delete(self.ssh_client_name)

        super().tearDown()

    def wait(self, ip, port, timeout):
        for _ in range(timeout):
            if j.sals.nettools.tcp_connection_test(ip, port, timeout=1):
                return True
            sleep(1)
        return False

    def test01_ubuntu_with_specific_node(self):
        """Test case for deploying Ubuntu with specific node.

        **Test Scenario**

        - Deploy Ubuntu.
        - Check that Ubuntu is reachable.
        """
        self.info("Deploy Ubuntu")
        name = self.random_name()
        ubuntu = deployer.deploy_ubuntu(
            solution_name=name,
            pool=self.pool_id,
            network=self.network_name,
            ssh=self.ssh_cl.public_key_path,
            node_automatic="NO",
        )
        self.solution_uuid = ubuntu.solution_id

        self.info("Check that Ubuntu is reachable")
        self.assertTrue(
            self.wait(ubuntu.ip_address, port=22, timeout=self.timeout),
            f"Ubuntu is not reached after {self.timeout} second",
        )

    @parameterized.expand(
        [
            ("kub_size", "vCPU: 2, RAM: 5 GiB, Disk Space: 50 GiB"),
            ("kub_size", "vCPU: 4, RAM: 16 GiB, Disk Space: 400 GiB"),
            ("kub_size", "vCPU: 8, RAM: 32 GiB, Disk Space: 100 GiB"),
        ]
    )
    def test02_kubernetes_with_different_sizes(self, _, kub_size):
        """Test case for Deploying a kubernetes with different size.

        **Test Scenario**

        - Deploy kubernetes.
        - Check that kubernetes is reachable.
        """
        self.info("Deploy kubernetes")
        name = self.random_name()
        secret = self.random_name()

        kubernetes = deployer.deploy_kubernetes(
            solution_name=name,
            secret=secret,
            network=self.network_name,
            ssh=self.ssh_cl.public_key_path,
            pools=self.pool_id,
            size=kub_size,
        )
        self.solution_uuid = kubernetes.solution_id
        self.info("Check that kubernetes is reachable")
        self.assertTrue(
            self.wait(kubernetes.ip_addresses[0], port=22, timeout=self.timeout),
            f"master is not reached after {self.timeout} second",
        )

    def test03_minio_with_with_master_slave(self):
        """Test case for deploying Minio with master/slave.

        **Test Scenario**

        - Deploy Minio with master/slave.
        - Check that Minio is reachable.
        """
        self.info("Deploy Minio with master/slave")
        name = self.random_name()
        username = self.random_name()
        password = self.random_name()
        minio = deployer.deploy_minio(
            solution_name=name,
            username=username,
            password=password,
            network=self.network_name,
            ssh=self.ssh_cl.public_key_path,
            container_pool=self.pool_id,
            setup="Master/Slave",
        )
        self.solution_uuid = minio.solution_id

        self.info("Check that Minio is reachable")
        self.assertTrue(
            self.wait(minio.ip_addresses[0], port=9000, timeout=self.timeout),
            f"minio is not reached after {self.timeout} second",
        )

    def test04_network_add_access(self):
        """Test case for adding access for network.

        **Test Scenario**

        - Deploy network.
        - Add access to this network.
        - Up wireguard.
        - Check that network is reachable.
        """
        self.info("Deploy network")
        name = self.random_name()
        network = deployer.create_network(solution_name=name)

        self.info("Add access to this network")
        access_network = deployer.add_access_to_network(name)

        self.info("Up wireguard")
        self.wg_conf_paths.append(f"/tmp/{self.random_name()}.conf")
        j.sals.fs.write_file(self.wg_conf_paths[-1], access_network.wgconf)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_conf_paths[-1]}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")
        sleep(5)
        _, out, err = j.sals.process.execute("sudo wg")
        TestCase().assertIn("latest handshake", out, f"out: {out}, err: {err}")

        self.info("Check that network is reachable")
        ip_address = access_network.wgconf.split()[-1]
        endpoint = ip_address.split(":")[0]
        res, out, err = j.sals.process.execute(f"ping -c 1 {endpoint}")
        self.assertFalse(res)

    @pytest.mark.skip("https://github.com/threefoldtech/tfgateway/issues/60")
    def test05_deploy_network_with_ipv6(self):
        """Test case for deploying a network with IPv6.

        **Test Scenario**

        - Deploy a 4to6 GW.
        - Get and up GW wireguard.
        - Deploy network with IPv6.
        - Up network wireguard.
        - Check that network is reachable.
        """

        self.info("Deploy a 4to6 GW")
        four_to6_gw = deployer.deploy_4to6gw()
        self.solution_uuid = four_to6_gw.solution_id

        self.info("Get and up GW wireguard")
        self.wg_conf_paths.append(f"/tmp/{self.random_name()}.conf")
        j.sals.fs.write_file(self.wg_conf_paths[-1], four_to6_gw.wgconf)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_conf_paths[-1]}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")

        self.info("Deploy network with IPv6")
        name = self.random_name()
        network = deployer.create_network(solution_name=name, ip_version="IPv6")

        self.info("Up network wireguard")
        self.wg_conf_paths.append(f"/tmp/{self.random_name()}.conf")
        j.sals.fs.write_file(self.wg_conf_paths[-1], network.wgconf)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_conf_paths[-1]}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")
        sleep(5)
        _, out, err = j.sals.process.execute("sudo wg")
        TestCase().assertIn("latest handshake", out, f"out: {out}, err: {err}")

        self.info("Check that network is reachable")
        ip_address = network.wgconf.split()[-1].split("]")[0]
        endpoint = ip_address.split("[")[1]
        res, out, err = j.sals.process.execute(f"ping -c 1 {endpoint}")
        self.assertFalse(res)

    def test06_network_with_specific_ip(self):
        """Test case for deploying a network with specific IP.

        **Test Scenario**

        - Deploy Nwtwork with specific IP.
        - Up wireguard.
        - Check that Network is reachable.
        """

        self.info("Deploy Nwtwork with specific IP")
        name = self.random_name()
        ip = "10.132.0.0/16"
        network = deployer.create_network(solution_name=name, ip_select="Configure IP range myself", ip_range=ip)

        self.info("Up wireguard")
        self.wg_conf_paths.append(f"/tmp/{self.random_name()}.conf")
        j.sals.fs.write_file(self.wg_conf_paths[-1], network.wgconf)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {self.wg_conf_paths[-1]}")
        TestCase().assertFalse(rc, f"out: {out} err: {err}")
        sleep(5)
        _, out, err = j.sals.process.execute("sudo wg")
        TestCase().assertIn("latest handshake", out, f"out: {out}, err: {err}")

        self.info("Check that Network is reachable")
        ip_address = network.wgconf.split()[-1]
        endpoint = ip_address.split(":")[0]
        res, out, err = j.sals.process.execute(f"ping -c 1 {endpoint}")
        self.assertFalse(res)

    def test07_generic_flist_with_non_exist_flist(self):
        """Test case for deploying a container with a generic flist.

        **Test Scenario**

        - Deploy a container with a none exist flist.
        - Check that generic flist deploying has been failed.
        """

        self.info("Deploy a container with a none exist flist")
        name = self.random_name()
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            generic_flist = deployer.deploy_generic_flist(
                solution_name=name,
                flist="https://hub.grid.tf/posix.3bot/non-exist.flist",
                pool=self.pool_id,
                network=self.network_name,
            )
            self.solution_uuid = generic_flist.solution_id

        self.info("Check that generic flist deploying has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test08_deploy_container_with_0_pool_units(self):
        """Test case for deploying a container with 0 pool units.

        **Test Scenario**

        - Deploy a pool with 0 unit.
        - Deploy a container with 0 unit pool.
        - Check that container deploying has been failed.
        """
        self.info("Deploy a pool with 0 unit")
        name = self.random_name()
        cu, su = 0, 0
        farm = self.get_farm_name().capitalize()
        pool = deployer.create_pool(solution_name=name, farm=farm, cu=cu, su=su, wallet_name="demos_wallet",)

        self.info("Deploy a container with 0 unit pool")
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            generic_flist = deployer.deploy_generic_flist(
                solution_name=name,
                flist="https://hub.grid.tf/ayoubm.3bot/dmahmouali-mattermost-latest.flist",
                pool=pool.pool_data.reservation_id,
                network=self.network_name,
            )
            self.solution_uuid = generic_flist.solution_id
        import pdb

        pdb.set_trace()
        self.info("Check that generic flist deploying has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test09_deploy_container_with_push_logs_to_redis(self):
        """Test case for deploying a container with push logs to redis server.

        **Test Scenario**

        - get redis server instance.
        - Deploy a container with push logs to redis server.
        - Check that container deploying has been failed.
        """
        self.info("get redis server instance")
        redis = j.clients.redis.get("redis_test")

        self.info("Deploy an ubuntu and push container logs to redis server")
