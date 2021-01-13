import pytest
from jumpscale.loader import j
from jumpscale.packages import polls
from tests.frontend.pages.Packages.packages import Packages
from tests.frontend.tests.base_tests import BaseTest


@pytest.mark.integration
class PackagesTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.packages = Packages(self.driver)
        self.packages.load()

    def test01_system_packages(self):
        """Test case for checking system packages list.

        **Test Scenario**

        - Check the system packages list.
          the package list that should be started by default with threebot server.
          ['auth', 'chatflows', 'admin', 'weblibs', 'tfgrid_solutions', 'backup']
        """
        system_packages_list = self.packages.get_system_packages()

        self.info("Check the system packages list")
        default_packages_list = ["auth", "chatflows", "admin", "weblibs", "tfgrid_solutions", "backup"]
        self.assertEqual(default_packages_list, list(system_packages_list.keys()), "not all default packages exist")

    def test02_add_install_delete_package(self):
        """Test case for adding a package and deleting it.

        **Test Scenario**

        - Add a package using GitURL.
        - Check that the package has been installed correctly.
        - Add a package using path.
        - Check that the package has been installed correctly.
        - Install another package.
        - Check that the package has been installed correctly.
        - Delete the three packages.
        - Check that the packages have been deleted successfully.
        """

        self.info("Add a package using GitURL")
        git_url = "https://github.com/threefoldtech/js-sdk/tree/development/jumpscale/packages/notebooks"
        self.packages.add_package(git_url=git_url)

        self.info("Check that the package has been Added correctly")
        installed_packages, available_packages = self.packages.get_installed_and_available_packages()
        self.assertNotIn("notebooks", available_packages.keys())
        self.assertIn("notebooks", installed_packages.keys())

        self.info("Add a package using path")
        path = j.sals.fs.dirname(polls.__file__)
        self.packages.add_package(path=path)

        self.info("Check that the package has been Added correctly")
        installed_packages, available_packages = self.packages.get_installed_and_available_packages()
        self.assertNotIn("polls", available_packages.keys())
        self.assertIn("polls", installed_packages.keys())

        self.info("Install another package")
        installed_package = self.packages.install_random_package()

        self.info("Check that the package has been installed correctly")
        installed_packages, available_packages = self.packages.get_installed_and_available_packages()
        self.assertNotIn(installed_package, available_packages.keys())
        self.assertIn(installed_package, installed_packages.keys())

        self.info("Delete the three packages")
        self.packages.delete_package("notebooks")
        self.packages.delete_package("polls")
        self.packages.delete_package(installed_package)

        self.info("Check that the packages have been deleted successfully")
        installed_packages, available_packages = self.packages.get_installed_and_available_packages()
        self.assertNotIn("notebooks", installed_packages.keys())
        self.assertNotIn("polls", installed_packages.keys())
        self.assertNotIn(installed_package, installed_packages.keys())

    def test03_open_in_browser(self):
        """Test case for testing open in browser button.

        **Test Scenario**

        - Check if threebot deployer package is installed ot not, If not install it.
        - Press open in browser button.
        - Check the current URL.
        """
        git_url = "https://github.com/threefoldtech/js-sdk/tree/development/jumpscale/packages/threebot_deployer"
        self.info("Check if threebot deployer package is installed ot not, If not install it")
        self.info("Press open in browser button")
        current_url = self.packages.open_in_browser(package="threebot_deployer", git_url=git_url)

        self.info("Check the current URL")
        self.assertEqual(current_url, "https://localhost/threebot_deployer/#/")

    def test04_chatflows(self):
        """Test case for testing chatflow window.

        **Test Scenario**

        - Check if threebot deployer package is installed ot not, If not install it.
        - Press chatflows button.
        - Check that the chatflow pop-up window appears.
        """
        git_url = "https://github.com/threefoldtech/js-sdk/tree/development/jumpscale/packages/threebot_deployer"
        self.info("Check if threebot deployer package is installed ot not, If not install it")
        self.info("Press chatflows button")
        cards_name = self.packages.chatflows(package="threebot_deployer", git_url=git_url)

        self.info("Check that the chatflow pop-up window appears")
        self.assertIn("Chatflows", cards_name)
