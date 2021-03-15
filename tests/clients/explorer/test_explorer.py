from os import environ
from random import randint, choice

from jumpscale.loader import j
from tests.base_tests import BaseTests


class Explorer(BaseTests):

    tname = environ.get("TNAME")
    email = environ.get("EMAIL")
    words = environ.get("WORDS")
    explorer_url = "https://explorer.testnet.grid.tf/api/v1"
    MYID_NAME = "identity_{}".format(randint(1, 1000))
    explorer = j.core.identity.me.explorer

    @classmethod
    def setUpClass(cls):
        if not all([cls.tname, cls.email, cls.words]):
            raise Exception("Please add (TNAME, EMAIL, WORDS) of your 3bot identity as environment variables")
        cls.me = None
        if j.core.identity.list_all() and hasattr(j.core.identity, "me"):
            cls.me = j.core.identity.me
        myid = j.core.identity.new(
            cls.MYID_NAME, tname=cls.tname, email=cls.email, words=cls.words, explorer_url=cls.explorer_url
        )
        myid.register()
        myid.set_default()
        myid.save()

    @classmethod
    def tearDownClass(cls):
        j.core.identity.delete(cls.MYID_NAME)
        if cls.me:
            cls.me.set_default()

    def test01_check_nodes(self):
        """Check the node lists in explorer client.

        **Test Scenario**

        - List all nodes.
        - Check that node list contains the node_id, farm_id, resources.
        """

        self.info("List all nodes")
        nodes = self.explorer.nodes.list()
        node = choice(nodes)

        self.info("Check that node list contains the node_id, farm_id, resources")

        self.assertIn("node_id", str(node))
        self.assertIn("farm_id", str(node))
        self.assertIn("total_resources", str(node))

    def test02_check_explorer_url(self):
        """Check the explorer URL.

        **Test Scenario**

        - Check the explorer url.
        - Make sure explorer_url "https://explorer.testnet.grid.tf/api/v1"
        """

        self.info("Check the explorer url")
        self.assertEquals(self.explorer.url, "https://explorer.testnet.grid.tf/api/v1")

    def test03_check_farms(self):
        """Check the farms lists in explorer client.

        **Test Scenario**

        - List all farms.
        - Check that farm list contains the wallet_addresses, id, location.
        """

        self.info("List all farms")
        farms = self.explorer.farms.list()
        farm = choice(farms)

        self.info("Check that farm list contains the wallet_addresses, id, location")
        self.assertTrue(hasattr(farm, "wallet_addresses"))
        self.assertTrue(hasattr(farm, "id"))
        self.assertTrue(hasattr(farm, "location"))
