import pytest
from jumpscale.loader import j
from redis import Redis
from solutions_automation import deployer
from tests.sals.automated_chatflows.chatflows_base import ChatflowsBase
from gevent import sleep
from unittest import TestCase


@pytest.mark.integration
class TFGridSolutionChatflows(ChatflowsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Accept admin T&C for testing identity.
        cls.accept_terms_conditions(type_="admin")

        # Create Network
        cls.network_name = cls.random_name()
        cls.wg_conf_path = f"/tmp/{cls.random_name()}.conf"
        network = deployer.create_network(solution_name=cls.network_name)
        j.sals.fs.write_file(cls.wg_conf_path, network.wgconf)
        rc, out, err = j.sals.process.execute(f"sudo wg-quick up {cls.wg_conf_path}")
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
        pool = deployer.create_pool(
            solution_name=cls.pool_name, cu=1, su=1, time_unit="Day", time_to_live=1, wallet_name="demos_wallet",
        )
        cls.pool_id = pool.pool_data.reservation_id

    @classmethod
    def tearDownClass(cls):
        # should stop threebot server.
        j.sals.process.execute(f"sudo wg-quick down {cls.wg_conf_path}")
        j.sals.fs.rmtree(path=cls.wg_conf_path)
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

    def test01_ubuntu(self):
        """Test case for deploying Ubuntu.

        **Test Scenario**

        - Deploy Ubuntu.
        - Check that Ubuntu is reachable.
        - Check that Ubuntu has been deployed with the same version.
        """
        self.info("Deploy Ubuntu.")
        name = self.random_name()
        ubuntu = deployer.deploy_ubuntu(
            solution_name=name, pool=self.pool_id, network=self.network_name, ssh=self.ssh_cl.public_key_path,
        )
        self.solution_uuid = ubuntu.solution_id

        self.info("Check that Ubuntu is reachable.")
        self.assertTrue(
            self.wait(ubuntu.ip_address, port=22, timeout=self.timeout),
            f"Ubuntu is not reached after {self.timeout} second",
        )

        self.info("Check that Ubuntu has been deployed with the same version.")
        localclient = j.clients.sshclient.get(self.ssh_client_name)
        localclient.sshkey = self.ssh_client_name
        localclient.host = ubuntu.ip_address
        localclient.save()
        self.solution_uuid = ubuntu.solution_id
        _, res, _ = localclient.sshclient.run("cat /etc/os-release")
        self.assertIn('VERSION_ID="18.04"', res)

    def test02_kubernetes(self):
        """Test case for Deploying a kubernetes.

        **Test Scenario**

        - Deploy kubernetes.
        - Check that kubernetes is reachable.
        - Check that kubernetes has been deployed with the same number of workers.
        """
        self.info("Deploy kubernetes.")
        name = self.random_name()
        secret = self.random_name()
        workernodes = j.data.idgenerator.random_int(1, 2)

        kubernetes = deployer.deploy_kubernetes(
            solution_name=name,
            secret=secret,
            network=self.network_name,
            workernodes=workernodes,
            ssh=self.ssh_cl.public_key_path,
            pools=self.pool_id,
        )
        self.solution_uuid = kubernetes.solution_id
        self.info("Check that kubernetes is reachable.")
        self.assertTrue(
            self.wait(kubernetes.ip_addresses[0], port=22, timeout=self.timeout),
            f"master is not reached after {self.timeout} second",
        )

        self.info("Check that kubernetes has been deployed with the same number of workers.")
        localclient = j.clients.sshclient.get(self.ssh_client_name)
        localclient.sshkey = self.ssh_client_name
        localclient.host = kubernetes.ip_addresses[0]
        localclient.user = "rancher"
        localclient.save()
        _, res, _ = localclient.sshclient.run("kubectl get nodes")

        res = res.splitlines()
        res = res[2:]  # Remove master node and table's head.
        self.assertEqual(workernodes, len(res))

    def test03_minio(self):
        """Test case for deploying Minio.

        **Test Scenario**

        - Deploy Minio.
        - Check that Minio is reachable.
        """
        self.info("Deploy Minio.")
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
        )
        self.solution_uuid = minio.solution_id

        self.info("Check that Minio is reachable.")
        self.assertTrue(
            self.wait(minio.ip_addresses[0], port=9000, timeout=self.timeout),
            f"minio is not reached after {self.timeout} second",
        )
        request = j.tools.http.get(f"http://{minio.ip_addresses[0]}:9000", verify=False, timeout=self.timeout)
        self.assertEqual(request.status_code, 403)

    def test04_monitoring(self):
        """Test case for deploying a monitoring solution.

        **Test Scenario**

        - Deploy a monitoring solution.
        - Check that Prometheus UI is reachable.
        - Check that Grafana UI is reachable.
        - Check that Redis is reachable.
        """
        self.info("Deploy a monitoring solution.")
        name = self.random_name()
        monitoring = deployer.deploy_monitoring(
            solution_name=name,
            network=self.network_name,
            ssh=self.ssh_cl.public_key_path,
            redis_pool=self.pool_id,
            prometheus_pool=self.pool_id,
            grafana_pool=self.pool_id,
        )
        self.solution_uuid = monitoring.solution_id
        self.info("Check that Prometheus UI is reachable. ")
        request = j.tools.http.get(
            f"http://{monitoring.ip_addresses[1]}:9090/graph", verify=False, timeout=self.timeout
        )
        self.assertEqual(request.status_code, 200)

        self.info("Check that Grafana UI is reachable.")
        request = j.tools.http.get(f"http://{monitoring.ip_addresses[2]}:3000", verify=False, timeout=self.timeout)
        self.assertEqual(request.status_code, 403)
        self.assertIn("login", request.content.decode())

        self.info("Check that Redis is reachable.")
        self.assertTrue(
            self.wait(monitoring.ip_addresses[0], port=6379, timeout=self.timeout),
            f"redis is not reached after {self.timeout} second",
        )
        redis = Redis(host=monitoring.ip_addresses[0])
        self.assertEqual(redis.ping(), True)

    def test05_generic_flist(self):
        """Test case for deploying a container with a generic flist.

        **Test Scenario**

        - Deploy a container with a flist.
        - Check that the container coreX is reachable.
        """
        self.info("Deploy a container with a flist.")
        name = self.random_name()
        generic_flist = deployer.deploy_generic_flist(
            solution_name=name,
            flist="https://hub.grid.tf/ayoubm.3bot/dmahmouali-mattermost-latest.flist",
            pool=self.pool_id,
            network=self.network_name,
        )
        self.solution_uuid = generic_flist.solution_id

        self.info("Check that the container coreX is reachable.")
        request = j.tools.http.get(f"http://{generic_flist.ip_address}:7681", verify=False, timeout=self.timeout)
        self.assertEqual(request.status_code, 200)

    def test06_exposed_flist(self):
        """Test case for exposing a container with generic flist.

        **Test Scenario**

        - Deploy a container with a flist.
        - Expose this container's coreX endpoint to a subdomain.
        - Check that the container coreX is reachable through the subdomain.
        """
        self.info("Deploy a container with a flist.")
        flist_name = self.random_name()
        deployer.deploy_generic_flist(
            solution_name=flist_name,
            flist="https://hub.grid.tf/ayoubm.3bot/dmahmouali-mattermost-latest.flist",
            pool=self.pool_id,
            network=self.network_name,
        )

        self.info("Expose this container's coreX endpoint to a subdomain.")
        sub_domain = self.random_name()
        exposed = deployer.deploy_exposed(
            type="flist", solution_to_expose=flist_name, sub_domain=sub_domain, tls_port="7681", port="7681"
        )
        self.solution_uuid = exposed.solution_id

        self.info("Check that the container coreX is reachable through the subdomain.")
        request = j.tools.http.get(f"http://{exposed.domain}", verify=False, timeout=self.timeout)
        self.assertEqual(request.status_code, 200)
