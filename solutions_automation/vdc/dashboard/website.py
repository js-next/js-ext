from solutions_automation.vdc.dashboard.common import CommonChatBot
from jumpscale.packages.vdc_dashboard.chats.website import WebsiteDeploy


class WebsiteAutomated(CommonChatBot, WebsiteDeploy):
    URL_MESSAGE = "Repository URL"
    BRANCH_MESSAGE = "Branch"
    SOURCE_DIR_MESSAGE = "Source directory"

    QS = {URL_MESSAGE: "url", BRANCH_MESSAGE: "branch", SOURCE_DIR_MESSAGE: "src_dir"}