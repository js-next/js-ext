import os
from random import randint
from jumpscale.loader import j
from tests.base_tests import BaseTests


class TestPackageManager(BaseTests):
    HOME_DIR = os.getenv("HOME")
    tname = os.environ.get("TNAME")
    email = os.environ.get("EMAIL")
    words = os.environ.get("WORDS")
    explorer_url = "https://explorer.testnet.grid.tf/api/v1"
    MYID_NAME = "identity_{}".format(randint(1, 1000))

    @classmethod
    def setUpClass(cls):
        myid = j.core.identity.new(
            cls.MYID_NAME, tname=cls.tname, email=cls.email, words=cls.words, explorer_url=cls.explorer_url
        )
        myid.register()
        j.core.identity.set_default(cls.MYID_NAME)
        myid.save()
        j.servers.threebot.start_default()

    @classmethod
    def tearDownClass(cls):
        j.core.identity.delete(cls.MYID_NAME)
        j.servers.threebot.default.stop()

    def test01_package_add_and_delete(self):
        """
        Test case for adding and deleting package in threebot server

        **Test scenario**
        #. Add a package.
        #. Check that the package has been added.
        #. Try to add wrong package, and make sure that the error has been raised.
        #. Delete a package.
        #. Check that the package is deleted correctly.
        #. Try to delete non exists package, and make sure that the error has been raised.
        """
        self.info("Add a package")
        marketplace = j.servers.threebot.default.packages.add(
            "{}/js-sdk/jumpscale/packages/marketplace/".format(self.HOME_DIR)
        )
        marketplace_dir = {
            "marketplace": {
                "name": "marketplace",
                "path": "{}/js-sdk/jumpscale/packages/marketplace/".format(self.HOME_DIR),
                "giturl": None,
                "kwargs": {},
            }
        }
        self.assertEqual(marketplace, marketplace_dir)

        self.info("Check that the package has been added")
        packages_list = j.servers.threebot.default.packages.list_all()
        self.assertIn("marketplace", packages_list)

        self.info("Try to add wrong package, and check that there is an error")
        with self.assertRaises(Exception) as error:
            j.servers.threebot.default.packages.add("test_wrong_package")
            self.assertIn("No such file or directory : 'test_wrong_package/package.toml'", error.exception.args[0])

        self.info("Delete a package")
        j.servers.threebot.default.packages.delete("marketplace")

        self.info("Check that the package is deleted correctly")
        packages_list = j.servers.threebot.default.packages.list_all()
        self.assertNotIn("marketplace", packages_list)

        self.info("Try to delete non exists package, and make sure that the error has been raised")
        with self.assertRaises(Exception) as error:
            j.servers.threebot.default.packages.delete("test_wrong_package")
            self.assertIn("test_wrong_package package not found", error.exception.args[0])

    def test02_list_all(self):
        """
        Test case for listing all package in threebot server

        **Test scenario**
         #. Add a package.
         #. List packages, the added package should be found.
         #. Delete the package.
         #. List packages again, the deleted package should not be found.
        """
        self.info("Add a package")
        self.assertTrue(
            j.servers.threebot.default.packages.add("{}/js-sdk/jumpscale/packages/codeserver/".format(self.HOME_DIR))
        )

        self.info("List packages, the added package should be found")
        packages_list = j.servers.threebot.default.packages.list_all()
        self.assertIn("codeserver", packages_list)

        self.info("delete the package")
        j.servers.threebot.default.packages.delete("codeserver")

        self.info("List packages again, the deleted package should not be found")
        packages_list = j.servers.threebot.default.packages.list_all()
        self.assertNotIn("codeserver", packages_list)
