from jumpscale.loader import j

import imp
import os
import sys
import toml
import shutil
import gevent
import signal
from urllib.parse import urlparse
from gevent.pywsgi import WSGIServer
from jumpscale.core.base import Base, fields
from jumpscale import packages as pkgnamespace
from jumpscale.sals.nginx.nginx import LocationType, PORTS, AcmeServer


GEDIS = "gedis"
GEDIS_HTTP = "gedis_http"
GEDIS_HTTP_HOST = "127.0.0.1"
GEDIS_HTTP_PORT = 8000
SERVICE_MANAGER = "service_manager"
CHATFLOW_SERVER_HOST = "127.0.0.1"
CHATFLOW_SERVER_PORT = 8552
DEFAULT_PACKAGES = {
    "auth": {"path": os.path.dirname(j.packages.auth.__file__), "giturl": ""},
    "chatflows": {"path": os.path.dirname(j.packages.chatflows.__file__), "giturl": ""},
    "admin": {"path": os.path.dirname(j.packages.admin.__file__), "giturl": ""},
    "weblibs": {"path": os.path.dirname(j.packages.weblibs.__file__), "giturl": ""},
    "tfgrid_solutions": {"path": os.path.dirname(j.packages.tfgrid_solutions.__file__), "giturl": ""},
    "backup": {"path": os.path.dirname(j.packages.backup.__file__), "giturl": ""},
    "vueui": {"path": os.path.dirname(j.packages.vueui.__file__), "giturl": ""},
}
DOWNLOADED_PACKAGES_PATH = j.sals.fs.join_paths(j.core.dirs.VARDIR, "downloaded_packages")


class NginxPackageConfig:
    def __init__(self, package):
        self.package = package
        self.nginx = j.sals.nginx.get("main")

    @property
    def default_config(self):
        default_server = {
            "name": "default",
            "ports": self.package.config.get("ports"),
            "locations": self.package.config.get("locations", []),
            "domain": self.package.default_domain,
            "letsencryptemail": self.package.default_email,
            "acme_server_type": self.package.default_acme_server_type,
            "acme_server_url": self.package.default_acme_server_url,
        }

        is_auth = self.package.config.get("is_auth", True)
        is_admin = self.package.config.get("is_admin", True)

        for static_dir in self.package.static_dirs:
            default_server["locations"].append(
                {
                    "is_auth": is_auth,
                    "is_admin": is_admin,
                    "type": "static",
                    "name": static_dir.get("name"),
                    "spa": static_dir.get("spa"),
                    "index": static_dir.get("index"),
                    "path_url": j.sals.fs.join_paths(self.package.base_url, static_dir.get("path_url").lstrip("/")),
                    "path_location": self.package.resolve_staticdir_location(static_dir),
                    "force_https": self.package.config.get("force_https", True),
                }
            )

        for bottle_server in self.package.bottle_servers:
            default_server["locations"].append(
                {
                    "is_auth": is_auth,
                    "is_admin": is_admin,
                    "type": "proxy",
                    "name": bottle_server.get("name"),
                    "host": bottle_server.get("host"),
                    "port": bottle_server.get("port"),
                    "path_url": j.sals.fs.join_paths(self.package.base_url, bottle_server.get("path_url").lstrip("/")),
                    "path_dest": bottle_server.get("path_dest"),
                    "websocket": bottle_server.get("websocket"),
                    "force_https": self.package.config.get("force_https", True),
                }
            )

        if self.package.actors_dir:
            default_server["locations"].append(
                {
                    "is_auth": is_auth,
                    "is_admin": is_admin,
                    "type": "proxy",
                    "name": "actors",
                    "host": GEDIS_HTTP_HOST,
                    "port": GEDIS_HTTP_PORT,
                    "path_url": j.sals.fs.join_paths(self.package.base_url, "actors"),
                    "path_dest": self.package.base_url,
                    "force_https": self.package.config.get("force_https", True),
                }
            )

        if self.package.chats_dir:
            default_server["locations"].append(
                {
                    "is_auth": is_auth,
                    "is_admin": is_admin,
                    "type": "proxy",
                    "name": "chats",
                    "host": CHATFLOW_SERVER_HOST,
                    "port": CHATFLOW_SERVER_PORT,
                    "path_url": j.sals.fs.join_paths(self.package.base_url, "chats"),
                    "path_dest": self.package.base_url + "/chats",  # TODO: temperoary fix for auth package
                    "force_https": self.package.config.get("force_https", True),
                }
            )

        return [default_server]

    def apply(self):
        default_ports = [PORTS.HTTP, PORTS.HTTPS]
        servers = self.default_config + self.package.config.get("servers", [])
        for server in servers:
            ports = server.get("ports", default_ports) or default_ports
            for port in ports:
                server_name = server.get("name")
                if server_name != "default":
                    server_name = f"{self.package.name}_{server_name}"

                website = self.nginx.get_website(server_name, port=port)
                website.ssl = server.get("ssl", port == PORTS.HTTPS)
                website.includes = server.get("includes", [])
                website.domain = server.get("domain", self.default_config[0].get("domain"))
                website.letsencryptemail = server.get(
                    "letsencryptemail", self.default_config[0].get("letsencryptemail")
                )
                website.acme_server_type = server.get(
                    "acme_server_type", self.default_config[0].get("acme_server_type")
                )
                website.acme_server_url = server.get("acme_server_url", self.default_config[0].get("acme_server_url"))

                for location in server.get("locations", []):
                    loc = None

                    location_name = location.get("name")
                    location_name = f"{self.package.name}_{location_name}"
                    location_type = location.get("type", "static")

                    if location_type == "static":
                        loc = website.get_static_location(location_name)
                        loc.spa = location.get("spa", False)
                        loc.index = location.get("index")
                        loc.path_location = location.get("path_location")

                    elif location_type == "proxy":
                        loc = website.get_proxy_location(location_name)
                        loc.scheme = location.get("scheme", "http")
                        loc.host = location.get("host")
                        loc.port = location.get("port", PORTS.HTTP)
                        loc.path_dest = location.get("path_dest", "")
                        loc.websocket = location.get("websocket", False)
                        loc.proxy_buffering = location.get("proxy_buffering", "")
                        loc.proxy_buffers = location.get("proxy_buffers")
                        loc.proxy_buffer_size = location.get("proxy_buffer_size")

                    elif location_type == "custom":
                        loc = website.get_custom_location(location_name)
                        loc.custom_config = location.get("custom_config")

                    if loc:
                        loc.location_type = location_type
                        path_url = location.get("path_url", "/")
                        if loc.location_type == LocationType.PROXY:
                            # proxy location needs / (as we append slash to the backend server too)
                            # and nginx always redirects to the same location with slash
                            # this way, requests will go to backend servers without double slashes...etc
                            if not path_url.endswith("/"):
                                path_url += "/"
                        else:
                            # for other locations, slash is not required
                            if path_url != "/":
                                path_url = path_url.rstrip("/")

                        loc.path_url = path_url
                        loc.force_https = location.get("force_https")
                        loc.is_auth = location.get("is_auth", False)
                        loc.is_admin = location.get("is_admin", False)

                website.save()
                website.configure()
                self.nginx.save()


class StripPathMiddleware(object):
    """
    a middle ware for bottle apps to strip slashes
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, e, h):
        e["PATH_INFO"] = e["PATH_INFO"].rstrip("/")
        return self.app(e, h)


class Package:
    def __init__(
        self,
        path,
        default_domain,
        default_email,
        giturl="",
        kwargs=None,
        default_acme_server_type=AcmeServer.LETSENCRYPT,
        default_acme_server_url=None,
    ):
        self.path = path
        self.giturl = giturl
        self._config = None
        self.name = j.sals.fs.basename(path.rstrip("/"))
        self.nginx_config = NginxPackageConfig(self)
        self._module = None
        self.default_domain = default_domain
        self.default_email = default_email
        self.default_acme_server_type = default_acme_server_type
        self.default_acme_server_url = default_acme_server_url
        self.kwargs = kwargs or {}

    def _load_files(self, dir_path):
        for file_path in j.sals.fs.walk_files(dir_path, recursive=False):
            file_name = j.sals.fs.basename(file_path)
            if file_name.endswith(".py"):
                name = f"{self.name}_{file_name[:-3]}"
                yield dict(name=name, path=file_path)

    def load_config(self):
        return toml.load(self.package_config_path)

    @property
    def package_config_path(self):
        return j.sals.fs.join_paths(self.path, "package.toml")

    @property
    def package_module_path(self):
        return j.sals.fs.join_paths(self.path, "package.py")

    @property
    def module(self):
        if self._module is None:
            package_file_path = j.sals.fs.join_paths(self.path, "package.py")
            if j.sals.fs.exists(package_file_path):
                module = imp.load_source(self.name, package_file_path)
                if not hasattr(module, self.name):
                    raise j.exceptions.Halt(f"missing class ({self.name}) in the package file")

                self._module = getattr(module, self.name)()
        return self._module

    @property
    def base_url(self):
        return j.sals.fs.join_paths("/", self.name)

    @property
    def config(self):
        if not self._config:
            self._config = self.load_config()
        return self._config

    @property
    def actors_dir(self):
        actors_dir = j.sals.fs.join_paths(self.path, self.config.get("actors_dir", "actors"))
        if j.sals.fs.exists(actors_dir):
            return actors_dir

    @property
    def chats_dir(self):
        chats_dir = j.sals.fs.join_paths(self.path, self.config.get("chats_dir", "chats"))
        if j.sals.fs.exists(chats_dir):
            return chats_dir

    @property
    def services_dir(self):
        services_dir = j.sals.fs.join_paths(self.path, self.config.get("services_dir", "services"))
        if j.sals.fs.exists(services_dir):
            return services_dir

    @property
    def static_dirs(self):
        return self.config.get("static_dirs", [])

    @property
    def bottle_servers(self):
        return self.config.get("bottle_servers", [])

    @property
    def actors(self):
        return self._load_files(self.actors_dir)

    @property
    def services(self):
        return self._load_files(self.services_dir)

    def resolve_staticdir_location(self, static_dir):
        """Resolves path for static location in case we need it
        absoulute or not

        static_dir.absolute_path true it will return the path directly
        if false will be relative to the path

        Args:
            static_dir (str): package.toml static dirs category

        Returns:
            str: package path
        """
        path_location = static_dir.get("path_location")
        absolute_path = static_dir.get("absolute_path", False)
        if absolute_path:
            return j.sals.fs.expanduser(path_location)
        return j.sals.fs.expanduser(j.sals.fs.join_paths(self.path, path_location))

    def get_bottle_server(self, file_path, host, port):
        module = imp.load_source(file_path[:-3], file_path)
        return WSGIServer((host, port), StripPathMiddleware(module.app))

    def preinstall(self):
        if self.module and hasattr(self.module, "preinstall"):
            self.module.preinstall()

    def install(self, **kwargs):
        if self.module and hasattr(self.module, "install"):
            self.module.install(**kwargs)

    def uninstall(self):
        if self.module and hasattr(self.module, "uninstall"):
            self.module.uninstall()

    def start(self):
        if self.module and hasattr(self.module, "start"):
            self.module.start(**self.kwargs)

    def stop(self):
        if self.module and hasattr(self.module, "stop"):
            self.module.stop()

    def restart(self):
        if self.module:
            self.module.stop()
            self.module.start()

    def exists(self):
        return j.sals.fs.exists(self.package_config_path)

    def is_valid(self):
        # more constraints, but for now let's say it's not ok if the main files don't exist
        return self.exists()


class PackageManager(Base):
    packages = fields.Typed(dict, default=DEFAULT_PACKAGES.copy())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._threebot = None

    @property
    def threebot(self):
        if self._threebot is None:
            self._threebot = j.servers.threebot.get()
        return self._threebot

    def get(self, package_name):
        if package_name in self.packages:
            package_path = self.packages[package_name]["path"]
            package_giturl = self.packages[package_name]["giturl"]
            package_kwargs = self.packages[package_name].get("kwargs", {})
            return Package(
                path=package_path,
                default_domain=self.threebot.domain,
                default_email=self.threebot.email,
                default_acme_server_type=self.threebot.acme_server_type,
                default_acme_server_url=self.threebot.acme_server_url,
                giturl=package_giturl,
                kwargs=package_kwargs,
            )

    def get_packages(self):
        all_packages = []

        # Add installed packages including outer packages
        for pkg in self.packages:
            package = self.get(pkg)
            if package and package.is_valid():
                if j.sals.fs.exists(package.path):
                    chatflows = True if package.chats_dir else False
                    all_packages.append(
                        {
                            "name": pkg,
                            "path": package.path,
                            "giturl": package.giturl,
                            "system_package": pkg in DEFAULT_PACKAGES.keys(),
                            "installed": True,
                            "frontend": package.config.get("frontend", False),
                            "chatflows": chatflows,
                        }
                    )
                else:
                    j.logger.error(f"path {package.path} for {pkg} doesn't exist anymore")
            else:
                j.logger.error("pkg {pkg} is in self.packages but it's None")

        # Add uninstalled sdk packages under j.packages
        for path in set(pkgnamespace.__path__):
            for pkg in os.listdir(path):
                pkg_path = j.sals.fs.join_paths(path, pkg)
                pkgtoml_path = j.sals.fs.join_paths(pkg_path, "package.toml")
                if pkg not in self.packages and j.sals.fs.exists(pkgtoml_path):
                    all_packages.append(
                        {
                            "name": pkg,
                            "path": j.sals.fs.dirname(getattr(j.packages, pkg).__file__),
                            "giturl": "",
                            "system_package": pkg in DEFAULT_PACKAGES.keys(),
                            "installed": False,
                        }
                    )

        return all_packages

    def list_all(self):
        return list(self.packages.keys())

    def add(self, path: str = None, giturl: str = None, **kwargs):
        # first check if public repo
        # TODO: Check if package already exists
        if not any([path, giturl]) or all([path, giturl]):
            raise j.exceptions.Value("either path or giturl is required")
        pkg_name = ""
        if giturl:
            url = urlparse(giturl)
            url_parts = url.path.lstrip("/").split("/")
            if len(url_parts) == 2:
                pkg_name = url_parts[1].strip("/")
                j.logger.debug(
                    f"user didn't pass a URL containing branch {giturl}, try to guess (master, main, development) in order"
                )
                if j.tools.http.get(f"{giturl}/tree/master").status_code == 200:
                    url_parts.extend(["tree", "master"])
                elif j.tools.http.get(f"{giturl}/tree/main").status_code == 200:
                    url_parts.extend(["tree", "main"])
                elif j.tools.http.get(f"{giturl}/tree/development").status_code == 200:
                    url_parts.extend(["tree", "development"])
                else:
                    raise j.exceptions.Value(f"couldn't guess the branch for {giturl}")
            else:
                pkg_name = url_parts[-1].strip("/")

            if len(url_parts) < 4:
                raise j.exceptions.Value(f"invalid git URL {giturl}")

            org, repo, _, branch = url_parts[:4]
            repo_dir = f"{org}_{repo}_{pkg_name}_{branch}"
            repo_path = j.sals.fs.join_paths(DOWNLOADED_PACKAGES_PATH, repo_dir)
            repo_url = f"{url.scheme}://{url.hostname}/{org}/{repo}"

            # delete repo dir if exists
            j.sals.fs.rmtree(repo_path)

            j.tools.git.clone_repo(url=repo_url, dest=repo_path, branch_or_tag=branch)
            toml_paths = list(
                j.sals.fs.walk(repo_path, "*", filter_fun=lambda x: str(x).endswith(f"{pkg_name}/package.toml"))
            )
            if not toml_paths:
                raise j.exceptions.Value(f"couldn't find {pkg_name}/package.toml in {repo_path}")
            path_for_package_toml = toml_paths[0]
            package_path = j.sals.fs.parent(path_for_package_toml)
            path = package_path

        package = Package(
            path=path,
            default_domain=self.threebot.domain,
            default_email=self.threebot.email,
            giturl=giturl,
            kwargs=kwargs,
        )

        # TODO: adding under the same name if same path and same giturl should be fine, no?
        # if package.name in self.packages:
        #     raise j.exceptions.Value(f"Package with name {package.name} already exists")

        # execute package install method
        package.install(**kwargs)

        # install package if threebot is started
        if self.threebot.started:
            self.install(package)
            self.threebot.nginx.reload()
        self.packages[package.name] = {
            "name": package.name,
            "path": package.path,
            "giturl": package.giturl,
            "kwargs": package.kwargs,
        }

        self.save()

        # Return updated package info
        return {package.name: self.packages[package.name]}

    def delete(self, package_name):
        if package_name in DEFAULT_PACKAGES:
            raise j.exceptions.Value("cannot delete default packages")
        package = self.get(package_name)
        if not package:
            raise j.exceptions.NotFound(f"{package_name} package not found")

        # remove bottle servers
        rack_servers = list(self.threebot.rack._servers)
        for bottle_server in rack_servers:
            if bottle_server.startswith(f"{package_name}_"):
                self.threebot.rack.remove(bottle_server)

        # stop background services
        if package.services_dir:
            for service in package.services:
                self.threebot.services.stop_service(service["name"])

        if self.threebot.started:
            # unregister gedis actors
            gedis_actors = list(self.threebot.gedis._loaded_actors.keys())
            for actor in gedis_actors:
                if actor.startswith(f"{package_name}_"):
                    self.threebot.gedis._system_actor.unregister_actor(actor)

            # unload chats
            try:
                if package.chats_dir:
                    self.threebot.chatbot.unload(package.chats_dir)
            except Exception as e:
                j.logger.warning(f"Couldn't unload the chats of package {package_name}, this is the exception {str(e)}")

            # reload nginx
            self.threebot.nginx.reload()

        # execute package uninstall method
        package.uninstall()

        self.packages.pop(package_name)
        self.save()

    def install(self, package):
        """install and apply package configrations

        Args:
            package ([package object]): get package object using [self.get(package_name)]

        Returns:
            [dict]: [package info]
        """
        sys.path.append(package.path + "/../")  # TODO to be changed
        package.preinstall()
        for static_dir in package.static_dirs:
            path = package.resolve_staticdir_location(static_dir)
            if not j.sals.fs.exists(path):
                raise j.exceptions.NotFound(f"Cannot find static dir {path}")

        # add bottle servers
        for bottle_server in package.bottle_servers:
            path = j.sals.fs.join_paths(package.path, bottle_server["file_path"])
            if not j.sals.fs.exists(path):
                raise j.exceptions.NotFound(f"Cannot find bottle server path {path}")

            bottle_app = package.get_bottle_server(path, bottle_server["host"], bottle_server["port"])
            self.threebot.rack.add(f"{package.name}_{bottle_server['name']}", bottle_app)

        # register gedis actors
        if package.actors_dir:
            for actor in package.actors:
                self.threebot.gedis._system_actor.register_actor(actor["name"], actor["path"], force_reload=True)

        # add chatflows actors
        if package.chats_dir:
            self.threebot.chatbot.load(package.chats_dir)

        # start background services
        if package.services_dir:
            for service in package.services:
                self.threebot.services.add_service(service["path"])

        # start servers
        self.threebot.rack.start()

        # apply nginx configuration
        package.nginx_config.apply()

        # execute package start method
        package.start()
        self.threebot.gedis_http.client.reload()
        self.threebot.nginx.reload()

    def reload(self, package_name):
        if self.threebot.started:
            package = self.get(package_name)
            if not package:
                raise j.exceptions.NotFound(f"{package_name} package not found")
            if package.services_dir:
                for service in package.services:
                    self.threebot.services.stop_service(service["name"])
            self.install(package)
            self.threebot.nginx.reload()
            self.save()
        else:
            raise j.exceptions.Runtime("Can't reload package. Threebot server is not started")

        # Return updated package info
        return {package.name: self.packages[package.name]}

    def _install_all(self):
        """Install and apply all the packages configurations
        This method shall not be called directly from the shell,
        it must be called only from the code on the running Gedis server
        """
        all_packages = self.list_all()
        for package in all_packages:
            if package not in DEFAULT_PACKAGES:
                j.logger.info(f"Configuring package {package}")
                pkg = self.get(package)
                if not pkg:
                    j.logger.error(f"can't get package {package}")
                else:
                    if pkg.path and pkg.is_valid():
                        self.install(pkg)
                    else:
                        j.logger.error(f"package {package} was installed before but {pkg.path} doesn't exist anymore.")

    def scan_packages_paths_in_dir(self, path):
        """Scans all packages in a path in any level and returns list of package paths

        Args:
            path (str): root path that has packages on some levels

        Returns:
            List[str]: list of all packages available under the path
        """
        filterfun = lambda x: str(x).endswith("package.toml")
        pkgtoml_paths = j.sals.fs.walk(path, filter_fun=filterfun)
        pkgs_paths = list(map(lambda x: x.replace("/package.toml", ""), pkgtoml_paths))
        return pkgs_paths

    def scan_packages_in_dir(self, path):
        """Gets a dict from packages names to packages paths existing under a path that may have jumpscale packages at any level.

        Args:
            path (str): root path that has packages on some levels

        Returns:
            Dict[package_name, package_path]: dict of all packages available under the path
        """
        pkgname_to_path = {}
        for p in self.scan_packages_paths_in_dir(path):
            basename = j.sals.fs.basename(p).strip()
            if basename:
                pkgname_to_path[basename] = p

        return pkgname_to_path


class ThreebotServer(Base):
    _package_manager = fields.Factory(PackageManager)
    domain = fields.String()
    email = fields.String()
    acme_server_type = fields.Enum(AcmeServer)
    acme_server_url = fields.URL()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rack = None
        self._gedis = None
        self._db = None
        self._gedis_http = None
        self._services = None
        self._packages = None
        self._started = False
        self._nginx = None
        self._redis = None
        self.rack.add(GEDIS, self.gedis)
        self.rack.add(GEDIS_HTTP, self.gedis_http.gevent_server)
        self.rack.add(SERVICE_MANAGER, self.services)

    def is_running(self):
        nginx_running = self.nginx.is_running()
        redis_running = self.redis.cmd.is_running() or j.sals.nettools.wait_connection_test(
            "127.0.0.1", 6379, timeout=1
        )
        gedis_running = j.sals.nettools.wait_connection_test("127.0.0.1", 16000, timeout=1)
        return nginx_running and redis_running and gedis_running

    @property
    def started(self):
        return self._started

    @property
    def nginx(self):
        if self._nginx is None:
            self._nginx = j.tools.nginx.get("default")
        return self._nginx

    @property
    def redis(self):
        if self._redis is None:
            self._redis = j.tools.redis.get("default")
        return self._redis

    @property
    def db(self):
        if self._db is None:
            self._db = j.core.db
        return self._db

    @property
    def rack(self):
        if self._rack is None:
            self._rack = j.servers.rack
        return self._rack

    @property
    def gedis(self):
        if self._gedis is None:
            self._gedis = j.servers.gedis.get("threebot")
        return self._gedis

    @property
    def gedis_http(self):
        if self._gedis_http is None:
            self._gedis_http = j.servers.gedis_http.get("threebot")
        return self._gedis_http

    @property
    def services(self):
        if self._services is None:
            self._services = j.tools.servicemanager.get("threebot")
        return self._services

    @property
    def chatbot(self):
        return self.gedis._loaded_actors.get("chatflows_chatbot")

    @property
    def packages(self):
        if self._packages is None:
            self._packages = self._package_manager.get(self.instance_name)
        return self._packages

    def check_dependencies(self):
        install_msg = "Visit https://github.com/threefoldtech/js-sdk/blob/development/docs/wiki/quick_start.md for installation guide"

        if not self.nginx.installed:
            raise j.exceptions.NotFound(f"nginx is not installed.\n{install_msg}")

        ret = shutil.which("certbot")
        if not ret:
            raise j.exceptions.NotFound(f"certbot is not installed.\n{install_msg}")

        rc, out, err = j.sals.process.execute("certbot plugins")
        if "* nginx" not in out:
            raise j.exceptions.NotFound(f"python-certbot-nginx is not installed.\n{install_msg}")

        if not self.redis.installed:
            raise j.exceptions.NotFound(f"redis is not installed.\n{install_msg}")

        ret = shutil.which("tmux")
        if not ret:
            raise j.exceptions.NotFound(f"tmux is not installed.\n{install_msg}")

        ret = shutil.which("git")
        if not ret:
            raise j.exceptions.NotFound(f"git is not installed.\n{install_msg}")

    def start(self, wait: bool = False):
        # start default servers in the rack
        # handle signals
        for signal_type in (signal.SIGTERM, signal.SIGINT, signal.SIGKILL):
            gevent.signal(signal_type, self.stop)

        # mark app as started
        if self.is_running():
            return

        self.check_dependencies()

        self.redis.start()
        self.nginx.start()
        self.rack.start()
        j.logger.register(f"threebot_{self.instance_name}")

        # add default packages
        for package_name in DEFAULT_PACKAGES:
            j.logger.info(f"Configuring package {package_name}")
            try:
                package = self.packages.get(package_name)
                self.packages.install(package)
            except Exception as e:
                self.stop()
                raise j.core.exceptions.Runtime(
                    f"Error happened during getting or installing {package_name} package, the detailed error is {str(e)}"
                ) from e

        # install all package
        self.packages._install_all()
        j.logger.info("Reloading nginx")
        self.nginx.reload()

        # mark server as started
        self._started = True
        j.logger.info(f"Threebot is running at http://localhost:{PORTS.HTTP} and https://localhost:{PORTS.HTTPS}")
        self.rack.start(wait=wait)  # to keep the server running

    def stop(self):
        server_packages = self.packages.list_all()
        for package_name in server_packages:
            package = self.packages.get(package_name)
            package.stop()
        self.nginx.stop()
        # mark app as stopped, do this before stopping redis
        j.logger.unregister()
        self.redis.stop()
        self.rack.stop()
        self._started = False
