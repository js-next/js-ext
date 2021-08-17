import os
import time
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from jumpscale.core.base import StoredFactory
from jumpscale.loader import j
from jumpscale.packages.admin.bottle.models import UserEntry
from tests.base_tests import BaseTests
from tests.frontend.pages.base import Base


class BaseTest(BaseTests):
    @classmethod
    def setUpClass(cls):
        # Set auto login config to disable ThreeFold Connect login.
        j.core.config.set("AUTO_LOGIN", True)

        # Get environment variables to create identity.
        cls.tname = os.environ.get("TNAME")
        cls.email = os.environ.get("EMAIL")
        cls.words = os.environ.get("WORDS")
        cls.explorer_url = "https://explorer.testnet.grid.tf/api/v1"
        if not all([cls.tname, cls.email, cls.words]):
            raise Exception("Please add (TNAME, EMAIL, WORDS) of your 3bot identity as environment variables")

        # Check if there is identity registered to set it back after the tests are finished.
        cls.me = None
        if j.core.identity.list_all() and hasattr(j.core.identity, "me"):
            cls.me = j.core.identity.me

        # Accept T&C for testing identity.
        cls.accept_t_c(tname=cls.tname)

        # Configure test identity and start threebot server.
        cls.identity_name = j.data.random_names.random_name()
        identity = j.core.identity.new(
            cls.identity_name, tname=cls.tname, email=cls.email, words=cls.words, explorer_url=cls.explorer_url
        )
        identity.register()
        identity.set_default()
        cls.server = j.servers.threebot.get("default")
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        # Disable auto login after the tests are finished.
        j.core.config.set("AUTO_LOGIN", False)

        # Stop threebot server and the testing identity.
        cls.server.stop()
        j.core.identity.delete(cls.identity_name)

        # Restore the user identity
        if cls.me:
            cls.me.set_default()

        # Remove userEntry for accepting T&C
        cls.user_factory.delete(cls.user_entry_name)

    def setUp(self):
        # Configure chrome driver and go to the entrypoint.
        options = Options()
        options.add_argument("--no-sandbox")
        # For browser's head mode comment the next 3 lines
        options.add_argument("headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("ignore-certificate-errors")
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        self.driver.maximize_window()
        self.login_endpoint = "/auth/auto_login"
        self.driver.get(urljoin(Base.base_url, self.login_endpoint))

    def tearDown(self):
        # Take screenshot for failure test.
        if self._outcome.errors:
            self.driver.save_screenshot(f"{self._testMethodName}.png")
        self.driver.quit()

    @classmethod
    def accept_t_c(self, tname):
        self.user_entry_name = f"{tname.replace('.3bot', '')}"
        self.user_factory = StoredFactory(UserEntry)
        user_entry = self.user_factory.get(self.user_entry_name)
        user_entry.has_agreed = True
        user_entry.tname = tname
        user_entry.save()
