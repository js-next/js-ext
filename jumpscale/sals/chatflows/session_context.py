from jumpscale.loader import j

BASE_DIR = f"{j.core.dirs.CFGDIR}/chatflows"


class CreateSessionContext:
    """
    """

    def __init__(self, dir_name):
        self.dir_name = dir_name

    def __enter__(self):
        # create new directory
        try:
            # create a new session dir
            path = f"{BASE_DIR}/{self.dir_name}/"
            j.sals.fs.mkdirs(path, exist_ok=False)

            # create a new session files
            # |_ answers
            # |_ status
            j.sals.fs.touch(f"{path}/answers")
            j.sals.fs.touch(f"{path}/status")
        except (FileExistsError, OSError) as e:
            j.logger.error(f"Can't create session directory with error {str(e)}")

    def __exit__(self, *exc):
        return self


class UpdateSessionContext:
    """
    """

    def __init__(self, dir_name: str, data: str, append: bool = True):
        self.dir_name = dir_name
        self.data = data
        self.append = append

    def __enter__(self):
        try:
            j.sals.fs.write_text(f"{BASE_DIR}/{self.dir_name}", f"{self.data}\n", append=self.append)
        except Exception as e:
            j.logger.error(f"Can't write in file {self.dir_name} with error {str(e)}")
        return self

    def __exit__(self, *exc):
        return self


class GoBackContext:
    """
    """

    def __init__(self, session_id: str, data: str, slide: bool = False):
        self.session_id = session_id
        self.data = data
        self.slide = slide

    def __enter__(self):
        try:
            # update the status
            j.sals.fs.write_text(f"{BASE_DIR}/{self.session_id}/status", f"{self.data}\n")

            text = j.sals.fs.read_text(f"{BASE_DIR}/{self.session_id}/answers")
            all_step_answers = text.split("{new_step}")[1:-1]
            last_step_answers = "\n".join(all_step_answers[-1].split("\n")[1:-2])
            if last_step_answers:
                # remove one answer
                answers = "{new_step}".join(all_step_answers[:-1].append(last_step_answers))
            else:
                # remove the last step answers
                answers = "{new_step}".join(all_step_answers[:-1])
            # write in fs
            j.sals.fs.write_text(f"{BASE_DIR}/{self.session_id}/answers", answers)

        except Exception as e:
            j.logger.error(f"Can't write in file {self.session_id} with error {str(e)}")
        return self

    def __exit__(self, *exc):
        return self


class DeleteSessionContext:
    """
    """

    def __init__(self, dir_name):
        self.dir_name = dir_name

    def __enter__(self):
        try:
            path = f"{BASE_DIR}/{self.dir_name}/"
            j.sals.fs.rmtree(path)
        except Exception as e:
            j.logger.error(f"Can't delete session directory with error {str(e)}")
        return self

    def __exit__(self, *exc):
        return self
