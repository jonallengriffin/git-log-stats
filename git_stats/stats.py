import subprocess
import sys

def run_git(command):
    if not isinstance(command, collections.Iterable):
        command = [command]
    command.insert(0, 'git')
    output = subprocess.check_output(command)
    return output

class Commit(object):
    def __init__(self, commitstr):
        pass


class CommitList(object):
    commits = []

    def __init__(self, logstr):
        pass

def cli(args=sys.argv[1:]):
    log = run_git(['log'])

    cl = CommitList(log)

if __name__ == '__main__':
    sys.exit(cli())

