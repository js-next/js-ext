from jumpscale.servers.gedis.baseactor import BaseActor, actor_method
from jumpscale.sals.chatflows.session_context import CreateSessionContext, DeleteSessionContext, UpdateSessionContext
from jumpscale.loader import j
import base64
import sys
import uuid
import importlib
import os


class ChatFlows(BaseActor):
    def __init__(self):
        super().__init__()
        self.chats = {}
        self.sessions = {}

    @actor_method
    def new(self, package: str, chat: str, client_ip: str, query_params: dict = None) -> dict:
        package_object = self.chats.get(package)
        if not package_object:
            raise j.exceptions.Value(f"Package {package} not found")

        chatflow = package_object.get(chat)
        if not chatflow:
            raise j.exceptions.Value(f"Chat {chat} not found")

        if query_params is None:
            query_params = {}
        obj = chatflow(**query_params)
        session_id = obj.session_id
        with CreateSessionContext(session_id):
            self.sessions[session_id] = obj
            return {"sessionId": session_id, "title": obj.title}

    @actor_method
    def fetch(self, session_id: str, restore: bool = False) -> dict:
        chatflow = self.sessions.get(session_id)
        if not chatflow:
            return {"payload": {"category": "end"}}

        result = chatflow.get_work(restore)
        j.logger.debug(result)
        if result["payload"].get("category") == "end":
            with DeleteSessionContext(session_id):
                self.sessions.pop(session_id)
        else:
            with UpdateSessionContext(f"{session_id}/status", result, False):
                return result
        return result

    @actor_method
    def validate(self, session_id: str) -> dict:
        path = f"{j.core.dirs.CFGDIR}/chatflows/{session_id}"
        if j.sals.fs.is_dir(path):
            # TODO:
            # load from fs
            # self.sessions[key] = chatflow.load_from_path(path)
            # answers.extend([ answer for answer in step_answers.split("\n") if answer])
            # return {"valid": True}
            j.logger.debug("dir exists")
        return {"valid": session_id in self.sessions}

    @actor_method
    def end(self, session_id: str) -> dict:
        with DeleteSessionContext(session_id):
            self.sessions.pop(session_id, None)
            return {"ended": True}

    @actor_method
    def report(self, session_id: str, result: str = None):
        chatflow = self.sessions.get(session_id)
        chatflow.set_work(result)

    @actor_method
    def back(self, session_id: str):
        chatflow = self.sessions.get(session_id)
        chatflow.go_back()

    @actor_method
    def chatflows_list(self) -> list:
        return list(self.chats.keys())

    def _scan_chats(self, path):
        package = j.sals.fs.basename(j.sals.fs.parent(path))
        for path in j.sals.fs.walk_files(path, recursive=False):
            if path.endswith(".py"):
                name = j.sals.fs.stem(path)
                yield path, package, name

    def _import_path(self, filepath):
        absolute_path = os.path.abspath(filepath)
        paths = sys.path[:]
        paths.sort(key=lambda p: len(p), reverse=True)
        for syspath in paths:
            absolute_sys_path = os.path.abspath(syspath)
            if absolute_path.startswith(absolute_sys_path):
                parts = absolute_path[len(absolute_sys_path) + 1 : -3].split(os.path.sep)
                if "__init__" in parts:
                    parts.remove("__init__")
                module_name = ".".join(parts)
                break
        else:
            module_name = absolute_path

        spec = importlib.util.spec_from_file_location(module_name, absolute_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @actor_method
    def load(self, path: str):
        for path, package, chat in self._scan_chats(path):
            module = self._import_path(path)
            if package not in self.chats:
                self.chats[package] = {}

            self.chats[package][chat] = module.chat

    @actor_method
    def unload(self, path: str):
        for _, package, chat in self._scan_chats(path):
            self.chats[package].pop(chat)


Actor = ChatFlows
