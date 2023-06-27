import os


class Constants:
    def __init__(self):
        self.SCRIPT_DIR = os.getcwd()
        self.LOGFILENAME = os.path.join(".", "jenkinsapi.log")
