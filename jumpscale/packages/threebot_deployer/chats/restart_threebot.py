from jumpscale.sals.marketplace import MarketPlaceAppsChatflow, deployer, solutions
from jumpscale.packages.threebot_deployer.bottle.utils import list_threebot_solutions, start_threebot_solution
from jumpscale.packages.threebot_deployer.models.user_solutions import ThreebotState
from jumpscale.packages.threebot_deployer.models import USER_THREEBOT_FACTORY
from jumpscale.sals.chatflows.chatflows import StopChatFlow, chatflow_step
from jumpscale.data.nacl.jsnacl import NACL
from jumpscale.loader import j


class ThreebotRedeploy(MarketPlaceAppsChatflow):
    FLIST_URL = "https://hub.grid.tf/waleedhammam.3bot/waleedhammam-js-sdk-latest.flist"
    SOLUTION_TYPE = "threebot"  # chatflow used to deploy the solution
    title = "3Bot"
    steps = [
        "choose_name",
        "enter_password",
        "new_expiration",
        "solution_extension",
        "deploy" "initializing",
    ]

    @chatflow_step(title="Choose 3Bot")
    def choose_name(self):
        self._init_solution()
        all_3bot_solutions = list_threebot_solutions(self.threebot_name)
        self.non_running_3bots = [
            threebot for threebot in all_3bot_solutions if threebot["state"] != ThreebotState.RUNNING.value
        ]
        self.non_running_names = {threebot["name"]: threebot for threebot in self.non_running_3bots}
        self.name = self.drop_down_choice(
            "Please select the 3Bot you want to start.", list(self.non_running_names.keys()), required=True
        )
        self.threebot_info = self.non_running_names[self.name]
        self.pool_id = self.threebot_info["compute_pool"]
        self.query = {
            "cru": self.threebot_info["cpu"] + 1,
            "mru": self.threebot_info["memory"] / 1024 + 1,
            "sru": self.threebot_info["disk_size"] / 1024 + 0.25,
        }

    @chatflow_step(title="New Expiration")
    def new_expiration(self):
        self.pool = j.sals.zos.get().pools.get(self.pool_id)
        cu, su = deployer.calculate_capacity_units(**self.query)
        expiration_time = min(self.pool.cus / cu, self.pool.sus / su)
        if expiration_time < 60 * 60:
            default_time = j.data.time.utcnow().timestamp + 1209600
            self.expiration = deployer.ask_expiration(
                self, default_time, pool_empty_at=j.data.time.utcnow().timestamp + expiration_time
            )
        else:
            self.expiration = 0

    def _verify_password(self, password):
        instance = USER_THREEBOT_FACTORY.get(f"threebot_{self.threebot_info['solution_uuid']}")
        identity_words = j.core.identity.get(instance.identity_name).words
        words = j.data.encryption.key_to_mnemonic(password.encode().zfill(32))
        return words == identity_words

    @chatflow_step(title="Password")
    def enter_password(self):
        message = "Please create the 3Bot password."
        self.password = self.secret_ask(message, required=True, max_length=32)
        while not self._verify_password(self.password):
            error = message + f"<br><br><code>Incorrect recovery password for 3Bot name {self.solution_name}</code>"
            self.password = self.secret_ask(error, required=True, max_length=32, md=True)

    @chatflow_step(title="Deploying", disable_previous=True)
    def deploy(self):
        self.md_show_update("Starting your 3Bot...")
        start_threebot_solution(self.username, self.threebot_info["solution_uuid"], self.password)

    @chatflow_step(title="Initializing", disable_previous=True)
    def initializing(self):
        self.md_show_update("Initializing your 3Bot ...")
        self.domain = self.threebot_info["domain"]
        self.threebot_url = f"https://{self.domain}/admin"
        if not j.sals.reservation_chatflow.wait_http_test(
            self.threebot_url, timeout=600, verify=not j.config.get("TEST_CERT")
        ):
            self.stop(f"Failed to initialize 3Bot on {self.threebot_url} , please contact support")
        self.domain = f"{self.domain}/admin"

    @chatflow_step(title="Success", disable_previous=True, final_step=True)
    def success(self):
        display_name = self.threebot_info["name"]
        message = f"""\
        # Your 3Bot instance {display_name} has been resurrected
        <br />\n
        - You can access it via the browser using: <a href="https://{self.domain}" target="_blank">https://{self.domain}</a>
        """
        self.md_show(dedent(message), md=True)


chat = ThreebotRedeploy
