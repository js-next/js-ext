from jumpscale.god import j


class weblibs:
    def __init__(self):
        self.url = "https://github.com/threefoldtech/jumpscaleX_weblibs"
        self.path = "/sandbox/code/github/"
        self.branch = "development"

    def install(self):
        """Called when package is added
        """
        if not j.sals.fs.exists(j.sals.fs.join_paths(self.path, "jumpscaleX_weblibs")):
            j.tools.git.clone_repo(url=self.url, dest=self.path, branch_or_tag=self.branch)

    def uninstall(self):
        """Called when package is deleted
        """
        pass

    def start(self):
        """Called when threebot is started
        """
        pass

    def stop(self):
        pass
