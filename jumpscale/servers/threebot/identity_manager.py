import binascii

import requests
from collections import namedtuple

from jumpscale.data.encryption import mnemonic
from jumpscale.data.nacl.jsnacl import NACL
from jumpscale.data.serializers import base64
from jumpscale.core import exceptions
from jumpscale.tools.console import ask_choice, ask_string, printcolors

NETWORKS = {"mainnet": "explorer.grid.tf", "testnet": "explorer.testnet.grid.tf", "devnet": "explorer.devnet.grid.tf"}

RESTART_CHOICE = "Restart from the begining"
REENTER_CHOICE = "Re-Enter your value"
CHOICES = [RESTART_CHOICE, REENTER_CHOICE]

IdentityInfo = namedtuple("IdentityInfo", ["identity", "email", "words", "explorer"])


class IdentityManager:
    def __init__(self, identity: str = "", email: str = None, words: str = None, explorer: str = None):
        self.identity = identity
        self.email = email
        self.words = words
        self.explorer = explorer

    def reset(self):
        self.identity = ""
        self.email = ""
        self.words = ""
        self.explorer = ""

    def _check_keys(self, user_explorer_key, user_app):
        if not user_app:
            return True
        pub_key_app = base64.decode(user_app["publicKey"])
        if binascii.unhexlify(user_explorer_key) != pub_key_app:
            return False
        return True

    def _get_user(self):
        response = requests.get(f"https://login.threefold.me/api/users/{self.identity}")
        if response.status_code == 404:
            raise exceptions.Value(
                "\nThis identity does not exist in 3bot mobile app connect, Please create an idenity first using 3Bot Connect mobile Application\n"
            )
        userdata = response.json()

        resp = requests.get("https://{}/explorer/users".format(self.explorer), params={"name": self.identity})
        if resp.status_code == 404 or resp.json() == []:
            # creating new user
            user = {}
            user["name"] = userdata["doublename"]
            user["pubkey"] = base64.decode(userdata["publicKey"]).hex()
            printcolors(
                f"\nWelcome {{CYAN}}{userdata['doublename']}{{WHITE}}. Creating a new record on {{CYAN}}{self.explorer}{{RESET}}.\n"
            )
            return user, userdata
        else:
            users = resp.json()

            if not self._check_keys(users[0]["pubkey"], userdata):
                raise exceptions.Value(
                    f"\nYour 3bot on {self.explorer} seems to have been previously registered with a different public key.\n"
                    f"The identity of {self.identity} is mismatched with 3bot connect app"
                    "Please contact support.grid.tf to reset it.\n"
                    "Note: use the same email registered on the explorer to contact support otherwise we cannot reset the account.\n"
                )

            if users:
                return (users[0], userdata)
            return None, userdata

    def _check_email(self, email):
        resp = requests.get("https://{}/explorer/users".format(self.explorer), params={"email": email})
        users = resp.json()
        if users:
            if users[0]["name"] == self.identity:
                return True
            else:
                return False
        else:
            return True

    def ask_identity(self, identity=None, explorer=None):
        def _fill_identity_args(identity, explorer):
            def fill_words():
                words = ask_string("Copy the phrase from your 3bot Connect app here: ")
                self.words = words

            def fill_identity():
                identity = ask_string("what is your threebot name (identity)? ")
                if "." not in identity:
                    identity += ".3bot"
                self.identity = identity

            if identity:
                if self.identity != identity and self.identity:
                    self.reset()
                self.identity = identity

            if explorer:
                self.explorer = explorer
            elif not self.explorer:
                response = ask_choice(
                    "Which network would you like to register to? ", ["mainnet", "testnet", "devnet", "none"]
                )
                self.explorer = NETWORKS.get(response, None)
            if not self.explorer:
                return True

            user, user_app = None, None
            while not user:
                fill_identity()
                try:
                    user, user_app = self._get_user()
                except exceptions.Value as e:
                    response = ask_choice(f"{e}What would you like to do? ", CHOICES)
                    if response == RESTART_CHOICE:
                        return False

            while not self.email:
                self.email = ask_string("What is the email address associated with your identity? ")
                if self._check_email(self.email):
                    break
                else:
                    self.email = None
                    response = ask_choice(
                        "This email is currently associated with another identity. What would you like to do? ",
                        CHOICES,
                    )
                    if response == RESTART_CHOICE:
                        return False

            print("Configured email for this identity is {}".format(self.email))

            # time to do validation of words
            hexkey = None
            while True:
                if not self.words:
                    fill_words()
                try:
                    seed = mnemonic.mnemonic_to_key(self.words.strip())
                    hexkey = NACL(seed).get_verify_key_hex()
                    if (user and hexkey != user["pubkey"]) or not self._check_keys(hexkey, user_app):
                        raise Exception
                    else:
                        return True
                except Exception:
                    choice = ask_choice(
                        "\nSeems one or more more words entered is invalid.\nWhat would you like to do? ", CHOICES,
                    )
                    if choice == RESTART_CHOICE:
                        return False
                    fill_words()

        while True:
            if _fill_identity_args(identity, explorer):
                identity_info = IdentityInfo(self.identity, self.email, self.words, self.explorer)
                return identity_info
