from time import time

import pytest
from jumpscale.loader import j
from solutions_automation import deployer
from tests.sals.automated_chatflows.chatflows_base import ChatflowsBase
from jumpscale.packages.threebot_deployer.bottle.utils import stop_threebot_solution
from jumpscale.packages.threebot_deployer.models import USER_THREEBOT_FACTORY


@pytest.mark.integration
class ThreebotChatflows(ChatflowsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Accept admin T&C for testing identity.
        cls.accept_terms_conditions(type_="marketplace")

        from jumpscale.packages import threebot_deployer

        path = j.sals.fs.dirname(threebot_deployer.__file__)
        threebot_deployer = j.servers.threebot.default.packages.add(path)

        cls.solution_uuid = ""
        cls.secret = ""

    @classmethod
    def tearDownClass(cls):
        # Remove userEntry for accepting T&C
        cls.user_factory.delete(cls.user_entry_name)
        super().tearDownClass()

    def tearDown(self):
        if self.solution_uuid and self.secret:
            stop_threebot_solution(self.tname, self.solution_uuid, self.secret)
        if hasattr(self, "ssh_client_name"):
            j.clients.sshclient.delete(self.ssh_client_name)

    def test01_deploy_threebot_on_past_expiration(self):
        """Test case for deploying a threebot with an expiration on the past.

        **Test Scenario**

        - Deploy a threebot with an expiration on the past.
        - Check that threebot deploying has been failed.
        """
        self.info("Deploy a threebot with an expiration on the past")
        name = self.random_name()
        self.secret = self.random_name()
        expiration = j.data.time.utcnow().timestamp - 60 * 15

        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
            self.solution_uuid = threebot.solution_id
        self.info("Check that threebot deploying has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test02_deploy_two_threebot_with_same_name(self):
        """Test case for deploying a threebot with an expiration on the past.

        **Test Scenario**

        - Deploy a threebot.
        - Try to deploy threebot with same name.
        - Check that threebot deploying has been failed.
        """
        self.info("Deploy a threebot")
        name = "testxbto"  # self.random_name()
        self.secret = "hassanhassan"  # self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 15

        self.info("Deploy a threebot")
        threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
        self.solution_uuid = threebot.solution_id

        self.info("Try to deploy threebot with same name")
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            threebot_with_same_name = deployer.deploy_threebot(
                solution_name=name, secret=self.secret, expiration=expiration, ssh=""
            )

        self.info("Check that threebot deploying has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test03_change_location_of_running_threebot(self):
        """Test case for changing the location of running threebot.

        **Test Scenario**

        - Deploy a threebot.
        - Try to change location for runing threebot.
        - Check that threebot changing location has been failed.
        """
        self.info("Deploy a threebot")
        name = "testxbto25"  # self.random_name()
        self.secret = "hassanhassan"  # self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 15
        threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
        self.solution_uuid = threebot.solution_id

        self.info("Try to deploy threebot with same name")
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            changed_threebot = deployer.change_threebot_location(name, self.secret, expiration_time=expiration)

        self.info("Check that threebot changing location has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test04_change_size_of_running_threebot(self):
        """Test case for changing the size of running threebot.

        **Test Scenario**

        - Deploy a threebot.
        - Try to change size for runing threebot.
        - Check that threebot changing size has been failed.
        """
        self.info("Deploy a threebot")
        name = "testxbto12"  # self.random_name()
        self.secret = "hassanhassan"  # self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 15
        threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
        self.solution_uuid = threebot.solution_id

        self.info("Try to change size for runing threebot")
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            changed_threebot = deployer.change_threebot_size(
                name, self.secret, flavor="Gold (CPU 2 - Memory 4 GB - Disk 4 GB [SSD])"
            )

        self.info("Check that threebot changing location has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test05_start_running_threebot(self):
        """Test case for start running threebot.

        **Test Scenario**

        - Deploy a threebot.
        - Try to start runing threebot.
        - Check that threebot running has been failed.
        """
        self.info("Deploy a threebot")
        name = "testxbto231"  # self.random_name()
        self.secret = "hassanhassan"  # self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 15
        threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
        self.solution_uuid = threebot.solution_id

        self.info("Try to start runing threebot")
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            changed_threebot = deployer.start_threebot(name, self.secret)

        self.info("Check that threebot running has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test06_start_running_threebot(self):
        """Test case for start running threebot.

        **Test Scenario**

        - Deploy a threebot.
        - Try to start runing threebot.
        - Check that threebot running has been failed.
        """
        self.info("Deploy a threebot")
        name = "testxbto2"  # self.random_name()
        self.secret = "hassanhassan"  # self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 15
        threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
        self.solution_uuid = threebot.solution_id

        self.info("Try to start runing threebot")
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            changed_threebot = deployer.start_threebot(name, self.secret)

        self.info("Check that threebot running has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test06_threebot_expiration_time(self):
        """Test case for check threebot expiration time.

        **Test Scenario**

        - Deploy a threebot.
        - Get the expiration value.
        - Check expiration value after one hour.
        """
        self.info("Deploy a threebot")
        name = "testxbto2115"  # self.random_name()
        self.secret = "hassanhassan"  # self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 60
        threebot = deployer.deploy_threebot(solution_name=name, secret=self.secret, expiration=expiration, ssh="")
        self.solution_uuid = threebot.solution_id

        timestamp_after_one_hour = self.timestamp_now + 60 * 60

        self.assertLess(int(threebot.expiration - timestamp_after_one_hour), 200)

    def test07_ssh_threebot(self):
        """Test case for ssh threebot.

        **Test Scenario**

        - Prepare ssh key.
        - Deploy threebot with ssh key.
        - Check ssh to threebot.
        """

        self.info("Prepare ssh key")
        # Prepare ssh
        self.ssh_client_name = self.random_name()
        if not j.sals.fs.exists("/tmp/.ssh"):
            j.core.executors.run_local('mkdir /tmp/.ssh && ssh-keygen -t rsa -f /tmp/.ssh/id_rsa -q -N "" ')
        self.ssh_cl = j.clients.sshkey.get(self.ssh_client_name)
        self.ssh_cl.private_key_path = "/tmp/.ssh/id_rsa"
        self.ssh_cl.load_from_file_system()
        self.ssh_cl.save()

        self.info("Deploy threebot with ssh key")
        name = self.random_name()
        self.secret = self.random_name()
        expiration = j.data.time.utcnow().timestamp + 60 * 15
        threebot = deployer.deploy_threebot(
            solution_name=name, secret=self.secret, expiration=expiration, ssh=self.ssh_cl.public_key_path
        )
        self.solution_uuid = threebot.solution_id

        self.info("Check ssh to threebot")
        localclient = j.clients.sshclient.get(self.ssh_client_name)
        localclient.sshkey = self.ssh_client_name
        localclient.host = threebot.addresses[0]
        localclient.save()
        _, res, _ = localclient.sshclient.run("cat /etc/os-release")
        self.assertIn('VERSION_ID="18.04"', res)