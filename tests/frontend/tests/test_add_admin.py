import pytest
import os
from jumpscale.loader import j
from tests.frontend.tests.base_tests import BaseTest
from solutions_automation import deployer
from urllib.parse import urljoin
from tests.frontend.pages.base import Base


@pytest.mark.integration
class AddAdminTests(BaseTest):
    def setUp(self):
        super().setUp()

        # logout from owner admin
        self.logout_endpoint = "/auth/logout/"
        self.driver.get(urljoin(Base.base_url, self.logout_endpoint))

        admin = os.environ.get("TEST_ADMIN")
        if not admin:
            raise Exception("Please add TEST_ADMIN")

        # add new admin
        j.core.identity.me.admins.append(admin)
        j.core.identity.me.save()

        super().accept_t_c(tname=admin)

        self.login_endpoint = "/auth/auto_login/"
        self.driver.get(urljoin(Base.base_url, f"{self.login_endpoint}?username={admin}"))

    def test01_deploy_pool(self):
        """Test case for creating a pool with new admin.

        **Test Scenario**

        - Create a pool with some CU and SU units.
        - Check that the pool has been created with the same units.
        """
        self.info("Create a pool with some CU and SU units.")
        name = self.random_name()
        cu = j.data.idgenerator.random_int(0, 2)
        su = j.data.idgenerator.random_int(1, 2)
        time_unit = "Day"
        time_to_live = j.data.idgenerator.random_int(1, 2)
        farm = self.get_farm_name().capitalize()
        pool = deployer.create_pool(
            solution_name=name,
            farm=farm,
            cu=cu,
            su=su,
            time_unit=time_unit,
            time_to_live=time_to_live,
            wallet_name="demos_wallet",
        )

        self.info("Check that the pool has been created with the same units.")
        reservation_id = pool.pool_data.reservation_id
        pool_data = j.sals.zos.get().pools.get(reservation_id)
        calculated_su = su * time_to_live * 60 * 60 * 24
        calculated_cu = cu * time_to_live * 60 * 60 * 24
        self.assertEqual(pool_data.cus, float(calculated_cu))
        self.assertEqual(pool_data.sus, float(calculated_su))
