import datetime
import json
import os
import sys
import subprocess
import time
from contextlib import contextmanager
from constants import Constants


class Utils:
    def __init__(self):
        self.constants = Constants()

    # print to both a log file and console
    # noinspection PyUnresolvedReferences
    def logprint(self, text, init_file=False, doexit=False, rc=0):
        text = "{d}: {t}".format(d=datetime.datetime.now(), t=text)
        # option to erase the log file
        if init_file:
            if os.path.exists(self.constants.LOGFILENAME):
                os.unlink(self.constants.LOGFILENAME)
        with open(self.constants.LOGFILENAME, "a") as f:
            f.write(text)
            f.flush()
        print(text)
        if doexit:
            sys.exit(rc)

    @contextmanager
    def pushd(self, new_dir):
        # works just like windows cmd pushd/popd
        # ref: http://stackoverflow.com/questions/6194499/python-os-system-pushddef
        previous_dir = os.getcwd()
        os.chdir(new_dir)
        yield
        os.chdir(previous_dir)

    def message_if_error(self, result, msg):
        if result['errorcode'] != 0:
            self.logprint(msg)
            return True
        return False

    @staticmethod
    def get_dir_size(directory):
        total_size = 0
        for path, dirs, files in os.walk(directory):
            for f in files:
                fp = os.path.join(path, f)
                total_size += os.path.getsize(fp)
        return total_size

    # noinspection PyUnresolvedReferences
    def do_interproject_delay(self, projdelay):
        if projdelay and projdelay > 0:
            self.logprint("\tinterproject delay for load balancing")
            time.sleep(projdelay)

    # exec a command and if error, print a message and exit with the specified code
    # noinspection PyUnresolvedReferences
    def exec_command_has_error(self, command, rc, msg):
        result = get_command_output(command)
        if result['errorcode'] == 0:
            self.logprint(result['stdout'])
            return False  # successful run
        else:
            self.logprint(msg, True, rc)  # command failed, exit

    @staticmethod
    def get_command_output(command, shell=False, debug=False):
        """
        Execute a shell command and return its output..
        @param command: The command line to execute, list first element is program, remaining elements are args
        @param shell: use a shell or not, True is yes, False is No, default = False
        @return: dictionary of errorcode, stdout, and stderr data
        """
        if debug:
            print("Executing: {c}".format(c=command))
        sp = subprocess.Popen(command.split(' '), stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              shell=shell)
        out, err = sp.communicate()
        return dict(errorcode=sp.returncode, stdout=out, stderr=err)

    # write json data structure to a file
    # noinspection PyUnresolvedReferences
    @staticmethod
    def write_json_to_file(data, filename):
        with open(os.path.join(self.constants.JSON_FILES, filename), "w") as f:
            json.dump(data, f, indent=4)
        return data

    def load_json_file(self, filename):
        repos = {}
        try:
            with open(filename, 'r') as jsonfile:
                repos = json.load(jsonfile)
        except Exception as e:
            self.logprint("Error {e} loading json file {f}".format(e=e, f=filename))
            exit(1)
        return repos

    # noinspection PyUnresolvedReferences
    def save_file(self, lines, name, pfx):
        filename = os.path.join(self.constants.DEPSLOG_DIR, "{p}-{pfx}.txt".format(p=name, pfx=pfx))
        with open(filename, "w") as f:
            for line in lines:
                f.writelines("{d}\n".format(d=line))
