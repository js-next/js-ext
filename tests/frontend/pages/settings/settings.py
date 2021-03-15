from tests.frontend.pages.base import Base
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class Settings(Base):
    def __init__(self, driver, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.driver = driver
        self.endpoint = "/admin/#/settings"

    def load(self):
        url = urljoin(self.base_url, self.endpoint)
        self.driver.get(url)

    def add_admin(self, name):
        self.select_card("Admins")

        admin_card = self.driver.find_element_by_class_name("v-dialog--active")
        input = admin_card.find_element_by_tag_name("input")
        input.send_keys(name)
        add_button = admin_card.find_elements_by_tag_name("button")
        add_button[1].click()
        self.wait(self.driver, "v-card__progress")

    def delete_admin(self, admin):
        admins = self.list("Admins")
        deleted_admin = [admins[a] for a in admins.keys() if a == admin][0]
        delete_button = deleted_admin.find_element_by_tag_name("button")
        delete_button.click()
        self.wait(self.driver, "progressbar")
        buttons = self.driver.find_elements_by_class_name("v-btn")
        next_button = [button for button in buttons if button.text == "CONFIRM"][1]
        next_button.click()
        self.wait(self.driver, "v-card__progress")

    def add_escalation_emails(self, email):
        self.select_card("Escalation Emails")
        escale_card = self.driver.find_element_by_class_name("v-dialog--active")
        input = escale_card.find_element_by_tag_name("input")
        input.send_keys(email)
        add_button = escale_card.find_elements_by_tag_name("button")
        add_button[1].click()
        self.wait(self.driver, "v-card__progress")

    def delete_escalation_emails(self, email):
        emails = self.list("Escalation Emails")
        deleted_email = [emails[e] for e in emails.keys() if e == email][0]
        delete_button = deleted_email.find_element_by_tag_name("button")
        delete_button.click()

    def add_identities(self, name, tname, email, words):
        self.select_card("Identities")
        v_cards = self.driver.find_elements_by_class_name("v-card")
        identity_card = [card for card in v_cards if "Add identity" in card.text][0]
        form = identity_card.find_element_by_tag_name("form")
        inputs_div = form.find_elements_by_class_name("v-text-field__slot")
        inputs = {"Display name": name, "3Bot name": tname, "Email": email, "Words": words}
        for input in inputs_div:
            if input.text in inputs.keys():
                input.find_element_by_tag_name("input").send_keys(inputs[input.text])

        self.click_button(self.driver, "ADD")
        self.wait(self.driver, "v-card__progress")

    def delete_identity(self, name):
        identities = self.list("Identities")
        identity = [identities[i] for i in identities.keys() if i == name][0]
        identity.click()
        v_cards = self.driver.find_elements_by_class_name("v-card")
        identity_details = [identity for identity in v_cards if identity == "Identity details"]
        buttons = identity_details.find_element_by_tag_name("button")
        buttons[0].click()

    def developer_options(self, label):
        self.wait(self.driver, "progressbar")
        cards = self.driver.find_elements_by_class_name("mt-0")
        developer_card = [card for card in cards if "Developer options" in card.text][0]
        options = developer_card.find_elements_by_class_name("v-input__slot")
        button = [option for option in options if option.text == label][0]
        button.click()

    def list(self, name):
        self.wait(self.driver, "progressbar")
        names = {}
        v_cards = self.driver.find_elements_by_class_name("v-card")
        card = [card for card in v_cards if name in card.text][0]
        admins = card.find_elements_by_class_name("ma-2")
        for a in admins:
            names[a.text] = a
        return names

    def select_card(self, name):
        self.wait(self.driver, "progressbar")
        v_cards = self.driver.find_elements_by_class_name("v-card")
        card = [card for card in v_cards if name in card.text][0]
        button = card.find_element_by_tag_name("button")
        button.click()
