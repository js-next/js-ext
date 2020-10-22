import os
from time import time

import pytest
from jumpscale.loader import j
from solutions_automation import deployer

from tests.sals.automated_chatflows.chatflows_base import ChatflowsBase


@pytest.mark.integration
class PoolChatflows(ChatflowsBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Accept admin T&C for testing identity.
        cls.accept_terms_conditions(type_="marketplace")
        cls.solution_uuid = ""

    @classmethod
    def tearDownClass(cls):
        # Remove userEntry for accepting T&C
        cls.user_factory.delete(cls.user_entry_name)
        super().tearDownClass()

    def tearDown(self):
        if self.solution_uuid:
            j.sals.reservation_chatflow.solutions.cancel_solution_by_uuid(self.solution_uuid)
        super().tearDown()

    def test01_create_pool(self):
        """Test case for create pool.

        **Test Scenario**
        - create pool
        - check that create pool is successful
        - check that cu and su as reserved
        """
        self.info("create pool")
        name = self.random_name()
        cu = j.data.idgenerator.random_int(0, 2)
        su = j.data.idgenerator.random_int(1, 2)
        time_unit = "Day"
        time_to_live = j.data.idgenerator.random_int(1, 2)
        pool = deployer.create_pool(
            solution_name=name, cu=cu, su=su, time_unit=time_unit, time_to_live=time_to_live, wallet_name="demos_wallet"
        )

        self.info("check that create pool is successful")
        reservation_id = pool.pool_data.reservation_id
        pool_data = j.sals.zos.get().pools.get(reservation_id)
        calculated_su = su * time_to_live * 60 * 60 * 24
        calculated_cu = cu * time_to_live * 60 * 60 * 24
        self.assertEqual(pool_data.cus, float(calculated_cu))
        self.assertEqual(pool_data.sus, float(calculated_su))

    def test02_extend_pool(self):
        """Test case for extend pool

        **Test Scenario**
        - create pool
        - extend pool
        - check that cu and su as reserved
        """
        self.info("create pool")
        name = self.random_name()
        pool = deployer.create_pool(solution_name=name, wallet_name="demos_wallet")
        reservation_id = pool.pool_data.reservation_id

        self.info("extend pool")
        cu = j.data.idgenerator.random_int(0, 2)
        su = j.data.idgenerator.random_int(1, 2)
        time_unit = "Day"
        time_to_live = j.data.idgenerator.random_int(1, 2)
        deployer.extend_pool(
            pool_name=name, wallet_name="demos_wallet", cu=cu, su=su, time_unit=time_unit, time_to_live=time_to_live,
        )

        self.info("check that cu and su as reserved")
        pool_data = j.sals.zos.get().pools.get(reservation_id)
        calculated_su = (su + 1) * time_to_live * 60 * 60 * 24
        calculated_cu = (cu + 1) * time_to_live * 60 * 60 * 24
        self.assertEqual(pool_data.cus, float(calculated_cu))
        self.assertEqual(pool_data.sus, float(calculated_su))
