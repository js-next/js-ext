from jumpscale.loader import j

import re
import gevent


class chatflows:
    def stop(self, **kwargs):
        """called when the server stopped
        """
        # check if there is an active chatflow
        path = f"{j.core.dirs.CFGDIR}/chatflows/"
        # set flag to disable stating new deployment with expiration 30 seconds
        _db = j.core.db
        _db.set("stopping_threebot_server", 1, ex=5 * 60)
        ready_to_stop = False
        while not ready_to_stop:
            if not j.sals.fs.is_dir(path) or j.sals.fs.is_empty_dir(path):
                j.logger.debug("there is no active deployment")
                break
            # check the creation time for every active chatflow and check if the previous is True then skip this chatflow and don't wait
            # have_to_wait is False means there is no payment or deployment started  so we can stop the chatflow
            for session_dir in j.sals.fs.walk(path, pat="*-*-*"):
                # read chatflow status
                replacements = {"\n": "", "False": "false", "True": "true", "'": '"'}
                replacements = dict((re.escape(key), value) for key, value in replacements.items())
                text = j.sals.fs.read_file(f"{session_dir}/status")
                pattern = re.compile("|".join(replacements.keys()))
                session_info = j.data.serializers.json.loads(
                    pattern.sub(lambda m: replacements[re.escape(m.group(0))], text)
                )
                have_to_wait = session_info["info"]["have_to_wait"]
                creation_time = j.data.time.get(session_info["info"]["creation_time"])
                diff_time = (j.data.time.now() - creation_time) / 60  # by min
                if have_to_wait:
                    break
            else:
                ready_to_stop = True
                break
            j.logger.warning("There is an active deployment, waiting 1 minuets")
            gevent.sleep(60)
