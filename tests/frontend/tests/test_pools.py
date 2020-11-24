import pytest
from jumpscale.loader import j
from tests.frontend.pages.pools.pools_solution import PoolsSolution
from tests.frontend.pages.wallets.wallets import Wallets
from tests.frontend.pages.pools.pools import Pools
from tests.frontend.tests.base_tests import BaseTest


@pytest.mark.integration
class PoolsTests(BaseTest):
    def test01_create_pool(self):
        """Test case for creating a pool.

        **Test Scenario**
        - Create a wallet.
        - Create a pool.
        - Check that the pool has been created in the pools card.
        - Delete the a wallet.
        """
        self.info("Create a wallet")
        wallet_name = self.random_name()
        wallets = Wallets(self.driver)
        wallets.load()
        wallets.add_funded(wallet_name)

        self.info("Create a pool")
        pool_name = self.random_name().lower()
        pools = PoolsSolution(self.driver)
        pools.load()
        pools.create(name=pool_name, wallet_name=wallet_name)

        self.info("Check that the pool has been created in the pools card")
        test_pools = Pools(self.driver)
        test_pools.load()
        pools_name = [name[0] for name in test_pools.list()]
        self.assertIn(pool_name, pools_name)

        self.info("Delete the wallet.")
        wallets.load()
        wallets.delete(wallet_name)

    def test02_extend_pool(self):
        """Test case for extending a pool.

        **Test Scenario**
        - Create a wallet.
        - Create a pool.
        - Extend this pool.
        - Check that pool has been Extended.
        - Delete the wallet.
        """
        self.info("Create a wallet.")
        wallet_name = self.random_name()
        wallets = Wallets(self.driver)
        wallets.load()
        wallets.add_funded(wallet_name)

        self.info("Create a pool")
        pool_name = self.random_name().lower()
        pools = PoolsSolution(self.driver)
        pools.load()
        pools.create(name=pool_name, wallet_name=wallet_name)

        self.info("Extend this pool")
        cu = j.data.idgenerator.random_int(0, 2)
        su = j.data.idgenerator.random_int(1, 2)
        time_unit = "Day"
        time_to_live = j.data.idgenerator.random_int(1, 2)
        pools = PoolsSolution(self.driver)
        pools.load()
        pools.extend(
            name=pool_name, wallet_name=wallet_name, cu=cu, su=su, duration_unit=time_unit, time_to_live=time_to_live
        )

        self.info("Check that pool has been Extended")
        test_pools = Pools(self.driver)
        test_pools.load()
        calculated_su = (su + 1) * time_to_live * 60 * 60 * 24
        calculated_cu = (cu + 1) * time_to_live * 60 * 60 * 24
        self.assertIn((pool_name, float(calculated_cu), float(calculated_su)), test_pools.list())

        self.info("Delete the wallet")
        wallets.load()
        wallets.delete(wallet_name)

    def test03_hide_pool(self):
        """Test case for hideing a pool.

        **Test Scenario**
        - Create a wallet.
        - Create a pool.
        - Check that the pool has been created in the pools card.
        - Hide this pool.
        - Check that the pool has been hidden from the pools card.
        - Delete the wallet.
        """
        self.info("Create a wallet")
        wallet_name = self.random_name()
        wallets = Wallets(self.driver)
        wallets.load()
        wallets.add_funded(wallet_name)

        self.info("Create a pool")
        pool_name = self.random_name().lower()
        pools = PoolsSolution(self.driver)
        pools.load()
        pools.create(name=pool_name, wallet_name=wallet_name)

        self.info("Check that the pool has been created in the pools card")
        test_pools = Pools(self.driver)
        test_pools.load()
        pools_name = [name[0] for name in test_pools.list()]
        self.assertIn(pool_name, pools_name)

        self.info("Hide this pool")
        test_pools.load()
        test_pools.hide_pool(pool_name)

        self.info("Check that the pool has been hidden from the pools card")
        test_pools.load()
        pools_name = [name[0] for name in test_pools.list()]
        self.assertNotIn(pool_name, pools_name)

        self.info("Delete the wallet")
        wallets.load()
        wallets.delete(wallet_name)
