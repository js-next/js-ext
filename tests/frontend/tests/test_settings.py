import pytest
from tests.frontend.pages.settings.settings import Settings
from tests.frontend.tests.base_tests import BaseTest
from jumpscale.loader import j
from gevent import sleep


@pytest.mark.integration
class SettingsTests(BaseTest):
    def test01_add_admins(self):
        """Test case for adding an admin and deleting it.

        **Test Scenario**

        - Add an admin.
        - Check that the admin has been added in the admins.
        - Delete the admin.
        - Check that the admin has been deleted from the admins.
        """
        settings = Settings(self.driver)
        settings.load()

        self.info("Add an admin")
        admin = f"{self.random_name()}.3bot"
        settings.add_admin(admin)

        self.info("Check that the admin has been added in the admins")
        admins = settings.list("Admins")
        self.assertIn(admin, admins.keys())

        self.info("Delete the admin")
        settings.delete_admin(admin)

        self.info("Check that the admin has been deleted from the admins")
        admins = settings.list("Admins")
        self.assertNotIn(admin, admins.keys())

    @pytest.mark.skip("can't get inputs name")
    def test02_add_identity(self):
        """Test case for adding an identity and deleting it.

        **Test Scenario**

        - Add an identity.
        - Check that the identity has been added in the identities.
        - Delete the identity.
        - Check that the identity has been deleted from the identities.
        """
        settings = Settings(self.driver)
        settings.load()

        self.info("Add an identity")
        name = self.random_name()
        settings.add_identities(name, self.tname, self.email, self.words)

        self.info("Check that the identity has been added in the identities")
        identities = settings.list("Identities")
        self.assertIn(name, identities.keys())

        self.info("Delete the identity")
        settings.delete_identity(name)

        self.info("Check that the identity has been deleted from the identities")
        identities = settings.list("Identities")
        self.assertNotIn(name, identities.keys())

    def test03_add_escalation_emails(self):
        """Test case for adding an email and deleting it.

        **Test Scenario**

        - Add an email.
        - Check that the email has been added in the escalation emails.
        - Delete the email.
        - Check that the email has been deleted from the escalation emails.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Add an email")
        email = j.data.fake.email()
        settings.add_escalation_emails(email)

        self.info("Check that the email has been added in the escalation emails")
        emails = settings.list("Escalation Emails")
        self.assertIn(email, emails.keys())

        self.info("Delete the email")
        settings.delete_escalation_emails(email)

        self.info("Check that the email has been deleted from the escalation emails")
        emails = settings.list("Escalation Emails")
        self.assertNotIn(email, emails.keys())

    def test04_allow_staging_ssl(self):
        """Test case for changing developer options (Allow staging ssl certificate).

        **Test Scenario**

        - Get the config for staging ssl certificate option.
        - Change this config.
        - Check that the config has been changed.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Get the config for staging ssl certificate option")
        option_before_changes = (j.core.config.get("TEST_CERT", False),)

        self.info("Change this config")
        settings.developer_options("Allow staging ssl certificate")
        sleep(3)
        option_after_changes = (j.core.config.get("TEST_CERT", False),)

        self.info("Check that the config has been changed")
        self.assertNotEqual(option_before_changes, option_after_changes)

    def test05_allow_over_provisioning(self):
        """Test case for changing developer options (Allow over provisioning).

        **Test Scenario**

        - Get the config for over provisioning.
        - Change this config.
        - Check that the config has been changed.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Get the config for over provisioning")
        option_before_changes = (j.core.config.get("OVER_PROVISIONING", False),)

        self.info("Change this config")
        settings.developer_options("Allow over provisioning")
        sleep(3)
        option_after_changes = (j.core.config.get("OVER_PROVISIONING", False),)

        self.info("Check that the config has been changed")
        self.assertNotEqual(option_before_changes, option_after_changes)

    def test06_enable_explorer_logs(self):
        """Test case for changing developer options (Enable explorer logs).

        **Test Scenario**

        - Get the config for explorer logs.
        - Change this config.
        - Check that the config has been changed.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Get the config for explorer logs")
        option_before_changes = (j.core.config.get("EXPLORER_LOGS", False),)

        self.info("Change this config")
        settings.developer_options("Enable explorer logs")
        sleep(3)
        option_after_changes = (j.core.config.get("EXPLORER_LOGS", False),)

        self.info("Check that the config has been changed")
        self.assertNotEqual(option_before_changes, option_after_changes)

    def test07_enable_sending_escalation_emails(self):
        """Test case for changing developer options (Enable sending escalation emails).

        **Test Scenario**

        - Get the config for sending escalation emails.
        - Change this config.
        - Check that the config has been changed.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Get the config for sending escalation emails")
        option_before_changes = (j.core.config.get("ESCALATION_EMAILS_ENABLED", False),)

        self.info("Change this config")
        settings.developer_options("Enable sending escalation emails")
        sleep(3)
        option_after_changes = (j.core.config.get("ESCALATION_EMAILS_ENABLED", False),)

        self.info("Check that the config has been changed")
        self.assertNotEqual(option_before_changes, option_after_changes)

    def test08_pools_auto_extension(self):
        """Test case for changing developer options (Pools auto extension).

        **Test Scenario**

        - Get the config for pools auto extension.
        - Change this config.
        - Check that the config has been changed.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Get the config for pools auto extension")
        option_before_changes = (j.core.config.get("AUTO_EXTEND_POOLS_ENABLED", False),)

        self.info("Change this config")
        settings.developer_options("Pools auto extension")
        sleep(3)
        option_after_changes = (j.core.config.get("AUTO_EXTEND_POOLS_ENABLED", False),)

        self.info("Check that the config has been changed")
        self.assertNotEqual(option_before_changes, option_after_changes)

    def test09_sort_nodes_by_SRU(self):
        """Test case for changing developer options (Sort nodes by SRU).

        **Test Scenario**

        - Get the config for sort nodes by SRU.
        - Change this config.
        - Check that the config has been changed.
        """

        settings = Settings(self.driver)
        settings.load()

        self.info("Get the config for sort nodes by SRU")
        option_before_changes = (j.core.config.get("SORT_NODES_BY_SRU", False),)

        self.info("Change this config")
        settings.developer_options("Sort nodes by SRU")
        sleep(3)
        option_after_changes = (j.core.config.get("SORT_NODES_BY_SRU", False),)

        self.info("Check that the config has been changed")
        self.assertNotEqual(option_before_changes, option_after_changes)
