import pytest
from random import randint
from tests.frontend.pages.workloads.workloads import workloads
from tests.frontend.tests.base_tests import BaseTest


@pytest.mark.integration
class WorkloadsTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.workloads = workloads(self.driver)
        self.workloads.load()

    def test01_delete_selected_workloads(self):
        """Check that selected workload has been deleted correctly.

        **Test Scenario**

        - Create a workload.
        - Delete selected workload.
        - Check that selected workload has been deleted correctly.
        """

        self.info("Create a workload")
        workload_name = "workload{}".format(randint(1, 500))
        workload_ID = self.workloads.create_workload(workload_name)

        self.info("Delete selected workload")
        self.workloads.delete_selected_workloads(workload_ID)

        self.info("Check that selected workload has been deleted correctly")
        workloads_status = self.workloads.check_selected_workloads_status(workload_ID)
        self.assertEquals(workloads_status, "DELETED")
