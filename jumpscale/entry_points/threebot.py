from gevent import monkey

monkey.patch_all(subprocess=False)  # noqa: E402

import sys

import click
import tempfile
import subprocess

from jumpscale.loader import j
from jumpscale.servers.threebot.identity_manager import IdentityManager
from jumpscale.sals.nginx.nginx import PORTS
from jumpscale.packages.admin.actors.wallet import Wallet

SERVICES_PORTS = {"nginx": 8999, "nginx_http": 80, "nginx_https": 443, "gedis": 16000}

THREEBOT_DEPS_BINS = ["nginx", "redis-server", "tmux", "git"]


def check_for_bins():
    for b in THREEBOT_DEPS_BINS:
        notfoundbins = []
        if not j.sals.process.is_installed(b):
            notfoundbins.append(b)

    if notfoundbins:
        bins = ",".join(notfoundbins)
        j.logger.error(
            f"{bins} not found in $PATH. Please check https://github.com/threefoldtech/js-sdk/blob/development/docs/wiki/installation.md for more info on installation requirements"
        )
        exit(1)
    else:
        bins = ",".join(THREEBOT_DEPS_BINS)
        j.logger.info(f"✅ binaries {bins} required are installed.")


def test_privileged_ports_bind():
    config = b"""\
worker_processes  1;
daemon off;
error_log stderr notice;
pid /tmp/nginxtest.pid;
events { worker_connections  1024; }
http {
    access_log off;
    server {
        listen       80;
        server_name  localhost;
    }
}
    """
    with tempfile.NamedTemporaryFile("w+b") as file:
        file.write(config)
        file.flush()
        proc = subprocess.Popen(["nginx", "-t", "-c", file.name], stderr=subprocess.PIPE)
        proc.wait()
        for line in proc.stderr.readlines():
            j.logger.debug(line.decode().strip())
        return proc.returncode == 0


@click.command()
@click.option("--identity", default=None, help="threebot name(i,e name.3bot)")
@click.option("--domain", default=None, help="threebot domain")
@click.option("--email", default=None, help="threebot ssl email")
@click.option("--development", default=False, is_flag=True, help="start in development mode (no identity is required)")
@click.option("--background/--no-background", default=False, help="threebot name(i,e name.3bot)")
@click.option(
    "--local/--no-local", default=False, help="run threebot server on none privileged ports instead of 80/443"
)
def start(identity=None, background=False, local=False, development=False, domain=None, email=None):
    """start 3Bot server after making sure identity is ok
    It will start with the default identity in j.me, if you'd like to specify an identity
    please pass the optional arguments

    usage: threebot start
    or: threebot start --identity <identity> --explorer <explorer>

    Args:
        identity (str, optional): threebot name. Defaults to None.
        explorer (str, optional): which explorer network to use: mainnet, testnet, devnet. Defaults to None.
    """
    if j.config.get("ANNOUNCED") is None:
        j.config.set("ANNOUNCED", False)

    create_wallets_if_not_exists()
    check_for_bins()
    PORTS.init_default_ports(local)
    SERVICES_PORTS["nginx_http"] = PORTS.HTTP
    SERVICES_PORTS["nginx_https"] = PORTS.HTTPS

    if not development and identity:
        if j.core.identity.find(identity):
            print(f"Setting default identity to {identity}\nStarting threebot server...")
            j.core.identity.set_default(identity)
            j.core.identity.me.save()
        else:
            j.tools.console.printcolors(
                "{RED}Identity %s is not set, please configure it or start with the default one{{RESET}}" % identity
            )
            sys.exit(1)

    if not development and not j.core.identity.list_all():
        identity_data = IdentityManager()
        identity_info = identity_data.ask_identity()
        me = j.core.identity.new(
            "default",
            tname=identity_info.identity,
            email=identity_info.email,
            words=identity_info.words,
            explorer_url=f"https://{identity_info.explorer}/api/v1",
        )
        me.register()
        me.save()

    used_ports = []
    ports_error_msg = ""
    for service_name, service_port in SERVICES_PORTS.items():
        if j.sals.process.is_port_listening(service_port):
            used_ports.append((service_name, service_port))
            ports_error_msg += f" {service_name}:{service_port}"

    msg = (
        f"{{RED}}Threebot server is running already or ports{{CYAN}}{ports_error_msg}{{RED}}\n"
        "are being held by your system\n"
        f"Please use {{WHITE}}threebot stop{{RED}} to stop your threebot server or free the ports to be able to start the threebot server{{RESET}}"
    )

    canbind = test_privileged_ports_bind()
    if not local and not canbind:
        j.tools.console.printcolors(
            "{RED}Nginx could not bind on privileged ports{RESET}, please run with local flag or give nginx extra permission 'sudo setcap CAP_NET_BIND_SERVICE=+eip $(which nginx)'"
        )
        sys.exit(1)
    if used_ports:
        j.tools.console.printcolors(msg)
        sys.exit(1)

    if background:
        cmd = j.tools.startupcmd.get("threebot_default")
        cmd.start_cmd = (
            f"jsng 'j.servers.threebot.start_default(wait=True, local={local}, domain={domain}, email={email})'"
        )
        cmd.process_strings_regex = [".*threebot_default.sh"]
        cmd.ports = [8000, 8999]
        cmd.start()
        for service_name, service_port in SERVICES_PORTS.items():
            if not j.sals.nettools.wait_connection_test("127.0.0.1", service_port, timeout=15):
                j.tools.console.printcolors(
                    f"{{RED}}Could not start threebot server. Service: {service_name}, Port {service_port} couldn't start in 15 seconds. Please try again {{RESET}}"
                )
                sys.exit(1)

        print("\n✅ Threebot server started\n")
        if j.sals.process.in_host():
            j.tools.console.printcolors(
                f"{{WHITE}}Visit admin dashboard at: {{GREEN}}http://localhost:{PORTS.HTTP}/\n{{RESET}}"
            )
    else:
        j.servers.threebot.start_default(wait=True, local=local, domain=domain, email=email)


@click.command()
def stop():
    """stops threebot server
    """
    threebot_pids = j.sals.process.get_pids("threebot")
    if len(threebot_pids) > 1:  # Check if threebot was started in foreground
        # Kill all other processes other than `threebot stop`
        mypid = j.sals.process.get_my_process().pid  # `threebot stop` pid
        for pid in threebot_pids:
            if pid != mypid:
                j.sals.process.kill(pid)
    else:
        threebot_cmd = j.tools.startupcmd.get("threebot_default")
        threebot_cmd.stop()
        j.servers.threebot.get().redis.stop()
        j.tools.nginx.get("default").stop()
    print("Threebot server Stopped")


@click.command()
def status():
    """return the status of threebot server
    """
    if j.servers.threebot.get().is_running():
        j.tools.console.printcolors("Server is {GREEN}running{RESET}")
    else:
        j.tools.console.printcolors("Server is {RED}stopped{RESET}")


@click.command()
@click.option("--identity", default=None, help="threebot name(i,e name.3bot)")
@click.option("--domain", default=None, help="threebot domain")
@click.option("--email", default=None, help="threebot ssl email")
@click.option("--development", default=False, is_flag=True, help="start in development mode (no identity is required)")
@click.option("--background/--no-background", default=False, help="threebot name(i,e name.3bot)")
@click.option(
    "--local/--no-local", default=False, help="run threebot server on none privileged ports instead of 80/443"
)
@click.pass_context
def restart(ctx, identity=None, background=False, local=False, development=False, domain=None, email=None):
    """restart threebot server
    """
    ctx.invoke(stop)
    ctx.invoke(
        start,
        identity=identity,
        background=background,
        local=local,
        development=development,
        domain=domain,
        email=email,
    )


@click.command()
@click.option("--all", default=False, is_flag=True, help="delete all of jumpscale config")
def clean(all=False):
    """deletes previous configurations of jumpscale
    """
    config_root = j.core.config.config_root

    if all:
        try:
            print("cleaning alerts...")
            try:
                j.tools.alerthandler.reset()
            except Exception as e:
                print("failed to clean up alerts")
                print(f"exception was {e} for debugging")

            answer = j.tools.console.ask_yes_no(f"Do you want to remove {config_root} ? ")
            if answer == "y":
                j.sals.fs.rmtree(config_root)
                print("Previous configuration is deleted.")

        except Exception as e:
            print(f"couldn't remove {config_root}")
            print(f"exception for debugging {e}")


@click.group()
def cli():
    pass


def have_wallets():
    wallets = j.clients.stellar.list_all()
    for wallet_name in wallets:
        wallet = j.clients.stellar.get(wallet_name)
        if wallet.network.value == "STD":
            return True
    return False


def create_main_wallet(wallet_name):
    wallet_actor = Wallet()
    try:
        wallet_actor.create_wallet(wallet_name)
    except Exception as e:
        j.logger.error(str(e))


def create_wallets_if_not_exists():
    main_wallet = have_wallets()
    if not j.core.identity.is_configured:
        j.logger.warning("skipping wallets creation, identity isn't configured yet")
        return
    else:
        if not main_wallet:
            create_main_wallet("main")


cli.add_command(start)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(restart)
cli.add_command(clean)


if __name__ == "__main__":
    cli()
