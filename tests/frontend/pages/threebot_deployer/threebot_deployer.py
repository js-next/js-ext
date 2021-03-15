from urllib.parse import urljoin

from jumpscale.loader import j
from tests.frontend.pages.base import Base


class ThreebotDeployer(Base):
    def __init__(self, driver, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.driver = driver
        self.endpoint = "threebot_deployer"

    def load(self):
        url = urljoin(self.base_url, self.endpoint)
        self.driver.get(url)

    def view_an_existing_3bot_button(self):
        self.load()
        view_my_existing_3bot_button = self.driver.find_elements_by_class_name("v-btn__content")[2]
        view_my_existing_3bot_button.click()
        self.wait(self.driver, "v-data-table__progress")

        # select All to show all 3bots
        footer = self.driver.find_element_by_class_name("v-data-footer")
        select_dev = footer.find_element_by_class_name("v-input__control")
        select_dev.click()
        options_list = self.driver.find_elements_by_class_name("v-list-item")
        options_list[3].click()

    def switch_driver_to_iframe(self):
        # switch driver to iframe
        self.wait(self.driver, "v-progress-linear__buffer")
        iframe = self.driver.find_elements_by_tag_name("iframe")[0]
        self.driver.switch_to_frame(iframe)

    def find_3bot_instance(self, action, my_3bot_instance_name):
        # Find correct 3bot instance row
        self.wait(self.driver, "v-progress-linear__buffer")
        table_box = self.driver.find_element_by_class_name("v-data-table")
        table = table_box.find_element_by_tag_name("table")
        rows = table.find_elements_by_tag_name("tr")
        actions = {"start": 0, "stop": 0, "delete": 2, "change_location": 3}
        i = actions[action]
        for row in rows:
            if row.text and row.text.split()[0] == my_3bot_instance_name:
                row.find_elements_by_class_name("v-btn__content")[i].click()
                break

    def payment_process(self, wallet_name):
        chat_box = self.driver.find_element_by_class_name("chat")
        payment = chat_box.find_element_by_class_name("mb-4").text
        payment_info = payment.splitlines()
        destination_wallet_address = payment_info[3]
        currency = payment_info[5]
        reservation_ID = payment_info[7]
        total_amount = payment_info[9].split()[0]

        wallet = getattr(j.clients.stellar, wallet_name)._get_asset(currency)
        j.clients.stellar.demos_wallet.transfer(
            destination_wallet_address,
            amount=total_amount,
            memo_text=reservation_ID,
            asset=f"{wallet.code}:{wallet.issuer}",
        )

    def deploy_new_3bot(self, my_3bot_instances, password, wallet_name):
        # Deploy a new 3bot button
        self.wait(self.driver, "v-progress-circular")

        deploy_new_3bot_button = self.driver.find_elements_by_class_name("v-btn__content")[1]
        deploy_new_3bot_button.click()
        self.wait(self.driver, "v-progress-circular")

        # switch driver to iframe
        iframe = self.driver.find_elements_by_tag_name("iframe")[0]
        self.driver.switch_to_frame(iframe)
        chat_box = self.driver.find_element_by_class_name("chat")

        # ThreeBot instance Name
        self.wait(self.driver, "v-progress-circular")
        name_element = chat_box.find_element_by_class_name("v-text-field__slot")
        name_input = name_element.find_element_by_tag_name("input")
        name_input.send_keys(my_3bot_instances)
        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-circular")
        self.wait(self.driver, "v-card__progress")

        # Choose how much resources the deployed solution will use.
        # We use 1 CPU, 2GB Memory, and 2GB[SSD] in this example.

        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-circular")

        # choose ssh file
        # ssh_element = chat_box.find_element_by_class_name("v-text-field__slot")
        # ssh_input = ssh_element.find_element_by_tag_name("input")
        # ssh_input.send_keys("/home/hassan/.ssh/id_rsa.pub")
        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-circular")

        # Threebot recovery password
        password_element = chat_box.find_element_by_class_name("v-text-field__slot")
        password_input = password_element.find_element_by_tag_name("input")
        password_input.send_keys(password)
        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-card__progress")
        self.wait(self.driver, "v-progress-circular")

        # The deployment location policy ( We here use it automatically )

        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-card__progress")

        self.wait(self.driver, "v-progress-circular")
        # wait for "Initializing your 3Bot ..."
        self.wait(self.driver, "v-progress-circular")
        # solution's expiration time
        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-card__progress")
        self.wait(self.driver, "v-progress-circular")

        # Payment process
        self.wait(self.driver, "v-progress-circular")
        self.payment_process(wallet_name=wallet_name)
        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-circular")
        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-circular")

        # Threebot instance URL
        threebot_instance_chat_box = self.driver.find_element_by_class_name("chat")
        threebot_instance_URL = threebot_instance_chat_box.find_element_by_class_name("v-card__text").text.split()[16]

        self.click_button(self.driver, "FINISH")
        return threebot_instance_URL

    def view_my_3bot(self, status):

        # View an existing 3bot button
        self.view_an_existing_3bot_button()

        self.wait(self.driver, "v-data-table__progress")

        # Select 3bot instances with certain status
        my_3bot_box = self.driver.find_element_by_class_name("v-select__selections")
        status_input = my_3bot_box.find_element_by_tag_name("input")
        status_input.send_keys(status)

        # List 3bot instances
        self.wait(self.driver, "v-progress-linear__buffer")
        table_box = self.driver.find_element_by_class_name("v-data-table")
        table = table_box.find_element_by_tag_name("table")
        rows = table.find_elements_by_tag_name("tr")

        my_3bot_instances = []
        for row in rows:
            my_3bot_instance = row.text.split()[0]
            my_3bot_instances.append(my_3bot_instance)

        return my_3bot_instances

    def delete_threebot_instance(self, my_3bot_instance_name, password):
        self.wait(self.driver, "v-progress-linear__buffer")
        # View an existing 3bot button
        self.view_an_existing_3bot_button()

        # Find correct 3bot instance row
        self.find_3bot_instance("delete", my_3bot_instance_name=my_3bot_instance_name)

        # Destroy 3bot box
        destroy_3bot = self.driver.find_element_by_class_name("v-card")
        input_password = destroy_3bot.find_element_by_tag_name("input")
        input_password.send_keys(password)

        # Click CONFIRM button
        self.click_button(self.driver, "CONFIRM")

        self.wait(self.driver, "v-card__process")

    def start_stopped_3bot_instance(self, my_3bot_instance_name, password, wallet_name):

        # View an existing 3bot button
        # self.view_an_existing_3bot_button()
        # v-progress-linear__indeterminate
        self.wait(self.driver, "v-progress-linear__indeterminate")

        self.find_3bot_instance("start", my_3bot_instance_name=my_3bot_instance_name)

        # switch driver to iframe
        self.switch_driver_to_iframe()

        self.wait(self.driver, "v-progress-circular")

        password_chat_box = self.driver.find_element_by_class_name("chat")
        input_password = password_chat_box.find_element_by_tag_name("input")
        input_password.send_keys(password)

        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "progressbar")
        self.wait(self.driver, "v-progress-circular")

        # Threebot instance URL
        threebot_instance_chat_box = self.driver.find_element_by_class_name("chat")
        threebot_instance_URL = threebot_instance_chat_box.find_element_by_class_name("v-card__text").text.split()[14]

        self.click_button(self.driver, "FINISH")
        return threebot_instance_URL

    def stop_running_3bot_instance(self, my_3bot_instance_name, password):
        self.wait(self.driver, "v-progress-linear__buffer")

        # View an existing 3bot button
        self.view_an_existing_3bot_button()

        # Find correct 3bot instance row
        self.find_3bot_instance("stop", my_3bot_instance_name=my_3bot_instance_name)

        password_chat_box = self.driver.find_element_by_class_name("v-card")
        input_password = password_chat_box.find_element_by_tag_name("input")
        input_password.send_keys(password)

        self.click_button(self.driver, "CONFIRM")
        self.wait(self.driver, "v-card__process")
        self.wait(self.driver, "v-progress-linear__buffer")

    def change_location(self, my_3bot_instance_name, password):
        self.wait(self.driver, "v-progress-linear__indeterminate")

        self.view_an_existing_3bot_button()
        self.find_3bot_instance("change_location", my_3bot_instance_name=my_3bot_instance_name)

        # switch driver to iframe
        self.switch_driver_to_iframe()

        self.wait(self.driver, "v-progress-circular")

        password_chat_box = self.driver.find_element_by_class_name("chat")
        input_password = password_chat_box.find_element_by_tag_name("input")
        input_password.send_keys(password)

        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "progressbar")
        self.wait(self.driver, "v-progress-circular")

        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-circular")

        self.click_button(self.driver, "NEXT")
        self.wait(self.driver, "v-progress-linear__indeterminate")
        self.wait(self.driver, "v-progress-circular")

        # Threebot instance URL
        threebot_instance_chat_box = self.driver.find_element_by_class_name("chat")
        threebot_instance_URL = threebot_instance_chat_box.find_element_by_class_name("v-card__text").text.split()[14]

        self.click_button(self.driver, "FINISH")
        return threebot_instance_URL
