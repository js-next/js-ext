import pytest
import urllib.request
import os
from jumpscale.loader import j
from random import randint
from tests.frontend.tests.base_tests import BaseTest
from tests.frontend.pages.threebot_deployer.threebot_deployer import ThreebotDeployer


@pytest.mark.integration
class ThreebotDeployerTests(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.info("Import a wallet")
        cls.wallet_name = "demos_wallet"
        cls.wallet_secret = os.environ.get("WALLET_SECRET")
        if not cls.wallet_secret:
            raise Exception("Please add WALLET_SECRET as environment variables")

        j.clients.stellar.get(cls.wallet_name, network="STD", secret=cls.wallet_secret)
        wallet = j.clients.stellar.get(cls.wallet_name)
        wallet.secret = cls.wallet_secret
        wallet.network = "STD"
        wallet.save()

    def tearDown(self):
        self.info("Stop and Delete the threebot instance")
        threebot_deployer = ThreebotDeployer(self.driver)
        threebot_deployer.load()
        threebot_deployer.stop_running_3bot_instance(my_3bot_instance_name=self.threebot_name, password=self.password)
        threebot_deployer.delete_threebot_instance(my_3bot_instance_name=self.threebot_name, password=self.password)
        super().tearDown()

    def test01_deploy_3bot(self):
        """Test case to test deploy and delete a 3bot instance

        **Test Scenario**

        - Create a threebot instance.
        - Check that the threebot instance has been created successfully.
        - Delete the threebot instance.
        """
        threebot_deployer = ThreebotDeployer(self.driver)
        threebot_deployer.load()
        self.info("Create a threebot instance")
        self.threebot_name = self.random_name().lower()
        self.password = randint(1, 500000)
        threebot_instance_url = threebot_deployer.deploy_new_3bot(
            my_3bot_instances=self.threebot_name, password=self.password, wallet_name=self.wallet_name
        )

        self.info("Check that the threebot instance has been created successfully")
        self.assertEqual(urllib.request.urlopen(threebot_instance_url).getcode(), 200)

        my_3bot_instances = threebot_deployer.view_my_3bot("RUNNING")
        self.assertIn(self.threebot_name, my_3bot_instances)

    def test02_start_and_stop_my_3bot_instance(self):
        """Test case to test start and stop a 3bot instance

        **Test Scenario**

        - Create a threebot instance.
        - Stopped the new created 3bot instance.
        - Check that the 3bot instance has been stopped successfully.
        - Start the 3bot instance.
        - Check that the 3bot instance has been started successfully.
        - Delete the 3bot instance.
        """
        threebot_deployer = ThreebotDeployer(self.driver)
        threebot_deployer.load()
        self.info("Create a threebot instance")
        self.threebot_name = self.random_name().lower()
        self.password = randint(1, 500000)
        threebot_deployer.deploy_new_3bot(
            my_3bot_instances=self.threebot_name, password=self.password, wallet_name=self.wallet_name
        )

        self.info("Stopped the new created 3bot instance")
        threebot_deployer.stop_running_3bot_instance(my_3bot_instance_name=self.threebot_name, password=self.password)

        self.info("Check that the 3bot instance has been stopped successfully")
        my_3bot_instances = threebot_deployer.view_my_3bot("STOPPED")
        self.assertIn(self.threebot_name, my_3bot_instances)

        self.info("Start the 3bot instance")
        threebot_instance_url = threebot_deployer.start_stopped_3bot_instance(
            my_3bot_instance_name=self.threebot_name, password=self.password, wallet_name=self.wallet_name
        )

        self.info("Check that the 3bot instance has been started successfully")
        self.assertEqual(urllib.request.urlopen(threebot_instance_url).getcode(), 200)
        my_3bot_instances = threebot_deployer.view_my_3bot("RUNNING")
        self.assertIn(self.threebot_name, my_3bot_instances)

    def test03_change_deployed_threebot_location(self):
        """Test case for changing a threebot location.

        **Test Scenario**

        - Create a threebot instance.
        - Stopped the new created 3bot instance.
        - Change the stopped threebot location.
        - Check that threebot is reachable.
        - Delete the 3bot instance.
        """
        threebot_deployer = ThreebotDeployer(self.driver)
        threebot_deployer.load()
        self.info("Create a threebot instance")
        self.threebot_name = self.random_name().lower()
        self.password = randint(1, 500000)
        threebot_deployer.deploy_new_3bot(
            my_3bot_instances=self.threebot_name, password=self.password, wallet_name=self.wallet_name
        )
        self.info("Stopped the new created 3bot instance")
        threebot_deployer.stop_running_3bot_instance(my_3bot_instance_name=self.threebot_name, password=self.password)

        self.info("Change the stopped threebot location")
        threebot_instance_url = threebot_deployer.change_location(
            my_3bot_instance_name=self.threebot_name, password=self.password
        )

        self.info("Check that the 3bot instance has been started successfully")
        self.assertEqual(urllib.request.urlopen(threebot_instance_url).getcode(), 200)
        my_3bot_instances = threebot_deployer.view_my_3bot("RUNNING")
        self.assertIn(self.threebot_name, my_3bot_instances)
