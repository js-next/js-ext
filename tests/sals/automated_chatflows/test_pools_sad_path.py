import pytest
from jumpscale.loader import j
from solutions_automation import deployer
from tests.sals.automated_chatflows.chatflows_base import ChatflowsBase
from gevent import sleep


@pytest.mark.integration
class PoolChatflows(ChatflowsBase):
    def tearDown(self):
        if hasattr(self, "wallet_name"):
            j.clients.stellar.delete(self.wallet_name)
        super().tearDown()

    def test01_create_pool_with_0_unit(self):
        """Test case for creating a pool with 0 units.

        **Test Scenario**

        - Create a pool with 0 CU and 0 SU units.
        - Check that the pool has been created with 0 units.
        """
        self.info("Create a pool with 0 CU and 0 SU units")
        name = self.random_name()
        cu, su = 0, 0
        farm = self.get_farm_name().capitalize()
        pool = deployer.create_pool(solution_name=name, farm=farm, cu=cu, su=su, wallet_name="demos_wallet",)

        self.info("Check that the pool has been created with 0 units")
        reservation_id = pool.pool_data.reservation_id
        pool_data = j.sals.zos.get().pools.get(reservation_id)
        self.assertEqual(pool_data.cus, 0.0)
        self.assertEqual(pool_data.sus, 0.0)

    def test02_create_pool_with_negative_units(self):
        """Test case for creating a pool with negative units.

        **Test Scenario**

        - Create a pool with negative units
        - Check that the pool creation has been failed
        """
        self.info("Create a pool with negative units.")
        name = self.random_name()
        cu = j.data.idgenerator.random_int(-2, -1)
        su = j.data.idgenerator.random_int(-2, -1)
        farm = self.get_farm_name().capitalize()

        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            pool = deployer.create_pool(solution_name=name, farm=farm, cu=cu, su=su, wallet_name="demos_wallet",)

        self.info("Check that the pool creation has been failed")
        calculated_cu = cu * 60 * 60 * 24
        error_message = (
            f"cannot unmarshal number {calculated_cu} into Go struct field ReservationData.data_reservation.cus"
        )
        self.assertIn(error_message, str(exp.value))

    def test03_create_pool_with_non_existing_farm(self):
        """Test case for creating a pool with non-existing farm.

        **Test Scenario**

        - Create a pool with non-existing farm.
        - Check that the pool creation has been failed.
        """
        self.info("Create a pool with non-existing farm")
        name = self.random_name()
        cu = j.data.idgenerator.random_int(1, 2)
        su = j.data.idgenerator.random_int(1, 2)
        farm = self.random_name()

        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            pool = deployer.create_pool(solution_name=name, farm=farm, cu=cu, su=su, wallet_name="demos_wallet",)

        self.info("Check that the pool creation has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def test04_create_pool_with_empty_wallet(self):
        """Test case for creating a pool with empty wallet.

        **Test Scenario**

        - Create empty wallet.
        - Create a pool with empty wallet.
        - Check that the pool creation has been failed.
        """
        self.info("Create empty wallet")
        self.wallet_name = self.random_name()
        self.create_wallet(self.wallet_name)

        self.info("Create a pool with empty wallet")
        name = self.random_name()
        farm = self.get_farm_name().capitalize()
        with pytest.raises(j.core.exceptions.exceptions.Runtime) as exp:
            pool = deployer.create_pool(solution_name=name, farm=farm, wallet_name=self.wallet_name,)

        self.info("Check that the pool creation has been failed")
        error_message = "Something wrong happened"
        self.assertIn(error_message, str(exp.value))

    def create_wallet(self, name, network="STD"):
        wallet = j.clients.stellar.new(name=name, network=network)
        try:
            wallet.activate_through_threefold_service()
        except Exception:
            j.clients.stellar.delete(name=name)
            raise j.exceptions.JSException("Error on wallet activation")
        wallet.save()
