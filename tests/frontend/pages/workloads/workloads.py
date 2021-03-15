from urllib.parse import urljoin
from solutions_automation import deployer
from tests.frontend.pages.base import Base


class workloads(Base):
    def __init__(self, driver, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.driver = driver
        self.endpoint = "/admin/#/workloads"

    def load(self):
        url = urljoin(self.base_url, self.endpoint)
        self.driver.get(url)

    def select_workload_by_ID(self, workload_ID):
        self.wait(self.driver, "v-progress-linear__buffer")

        # Select workloads by ID.
        search_ID_box = self.driver.find_element_by_class_name("v-text-field__slot")
        input_search_ID = search_ID_box.find_element_by_tag_name("input")
        input_search_ID.send_keys(workload_ID)

        # Check Box wth all selected workload
        ID = self.driver.find_elements_by_class_name("v-data-table__checkbox")
        click_ID = ID[1].find_element_by_class_name("v-icon")
        click_ID.click()

    def create_workload(self, workload_name):
        test_network = deployer.create_network(solution_name=workload_name)
        test_network_dict = test_network.config
        return int(test_network_dict.get("ids")[0])

    def delete_selected_workloads(self, workload_ID):
        self.load()
        self.select_workload_by_ID(workload_ID)

        # Delete all selected workloads
        self.click_button(self.driver, "DELETE SELECTED")

        # Click confirm
        self.click_button(self.driver, "CONFIRM")

    def check_selected_workloads_status(self, workload_ID):
        self.load()
        self.driver.refresh()
        self.wait(self.driver, "v-progress-linear__buffer")
        self.select_workload_by_ID(workload_ID)
        return self.driver.find_elements_by_class_name("text-start")[10].text
