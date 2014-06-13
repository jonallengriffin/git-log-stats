import argparse
import collections
import json
import os
import re
import subprocess
import sys

def run_git(command):
    command = command[:]
    if not isinstance(command, collections.Iterable):
        command = [command]
    command.insert(0, 'git')
    try:
        output = subprocess.check_output(command)
    except subprocess.CalledProcessError:
        sys.exit(1)
    return output


class LogStats(object):
    _authors = None
    _commits = None
    _lines_added = None
    _lines_deleted = None
    _files_touched = None
    _files_added = None
    _files_deleted = None
    _files_modified = None
    _diff = None

    def __init__(self, from_ref=None, to_ref=None):
        if not from_ref and to_ref:
            print("must specify 'from_ref' if 'to_ref specified.")
            sys.exit(1)

        self.from_ref = from_ref
        self.to_ref = to_ref

    @property
    def diff(self):
        if not self._diff:
            command = ['diff', '--stat']
            if self.from_ref:
                if self.to_ref:
                    command.append('%s..%s' % (self.from_ref, self.to_ref))
                else:
                    command.append(self.from_ref)
            output = run_git(command)

            lastline = output.splitlines()[-1]
            m = re.search(r'''(\d+) files changed(.*?)(\d+) insertions(.*?)(\d+) deletions''', lastline)
            if not m:
                raise ValueError("output not found")
            self._diff = {
                'files': m.group(1),
                'insertions': m.group(3),
                'deletions': m.group(5)
            }

        return self._diff

    @property
    def commits(self):
        if not self._commits:
            command = ['log', '--numstat', '--no-merges', '--pretty=format:{"commit":"%H","author":"%an <%ae>","date":"%ad","message":"%f","parents":"%p","files":[]}']
            if self.from_ref:
                if self.to_ref:
                    command.append('%s..%s' % (self.from_ref, self.to_ref))
                else:
                    command.append(self.from_ref)
            output = run_git(command)

            self._commits = []
            commit = None
            for line in output.splitlines():
                try:
                    temp_commit = json.loads(line)
                    if commit:
                        self._commits.append(commit)
                    commit = temp_commit
                except ValueError:
                    if line:
                        stats = line.split()
                        commit['files'].append({'added': stats[0], 'deleted': stats[1], 'path': stats[2]})
            self._commits.append(commit)
        return self._commits

    @property
    def total_commits(self):
        return len(self.commits)

    @property
    def authors(self):
        if not self._authors:
            self._authors = set([c['author'] for c in self.commits])
        return self._authors

    @property
    def total_authors(self):
        return len(self.authors)

    @property
    def lines_added(self):
        if not self._lines_added:
            self._lines_added = 0
            for c in self.commits:
                for f in c['files']:
                    try:
                        self._lines_added += int(f['added'])
                    except ValueError:
                        # binary files are denoted by -
                        pass
        return self._lines_added

    @property
    def lines_deleted(self):
        if not self._lines_deleted:
            self._lines_deleted = 0
            for c in self.commits:
                for f in c['files']:
                    try:
                        self._lines_deleted += int(f['deleted'])
                    except ValueError:
                        # binary files are denoted by -
                        pass
        return self._lines_deleted

    @property
    def files_touched(self):
        if not self._files_touched:
            command = ['whatchanged', '--pretty=format:']
            if self.from_ref:
                if self.to_ref:
                    command.append('%s..%s' % (self.from_ref, self.to_ref))
                else:
                    command.append(self.from_ref)
            output = run_git(command)

            self._files_touched = set()
            for line in output.splitlines():
                line = line.strip()
                if line:
                    line = line.split()
                    self._files_touched.add((line[-1], line[-2]))
        return self._files_touched

    @property
    def files_changed(self):
        return set([f[0] for f in self.files_touched])

    @property
    def total_files_changed(self):
        return len(self.files_changed)

    @property
    def files_added(self):
        if not self._files_added:
            self._files_added = set([f[0] for f in self.files_touched if f[1] == 'A'])
        return self._files_added

    @property
    def total_files_added(self):
        return len(self.files_added)

    @property
    def files_deleted(self):
        if not self._files_deleted:
            self._files_deleted = set([f[0] for f in self.files_touched if f[1] == 'D'])
        return self._files_deleted

    @property
    def total_files_deleted(self):
        return len(self.files_deleted)

    @property
    def files_modified(self):
        if not self._files_modified:
            self._files_modified = set([f[0] for f in self.files_touched if f[1] == 'M'])
        return self._files_modified

    @property
    def total_files_modified(self):
        return len(self.files_modified)

    @property
    def test_files_added(self):
        return set([f for f in self.files_added if 'test' in os.path.basename(f) and (os.path.basename(f).endswith('.js') or os.path.basename(f).endswith('.py'))])

    @property
    def total_test_files_added(self):
        return len(self.test_files_added)

    @property
    def test_files_deleted(self):
        return set([f for f in self.files_deleted if 'test' in os.path.basename(f) and (os.path.basename(f).endswith('.js') or os.path.basename(f).endswith('.py'))])

    @property
    def total_test_files_deleted(self):
        return len(self.test_files_deleted)

    @property
    def test_files_modified(self):
        return [f for f in self.files_modified if 'test' in os.path.basename(f) and (os.path.basename(f).endswith('.js') or os.path.basename(f).endswith('.py'))]

    @property
    def total_test_files_modified(self):
        return len(self.test_files_modified)


def cli(args=sys.argv[1:]):
    parser = argparse.ArgumentParser()
    parser.add_argument('--from', dest='from_ref', default=None,
                        help='Git ref to start collecting stats at.')
    parser.add_argument('--to', dest='to_ref', default=None,
                        help='Git ref to stop collecting stats at.')
    args = parser.parse_args(args)

    stats = LogStats(from_ref=args.from_ref, to_ref=args.to_ref)
    diff = stats.diff
    print("Total commits: %s" % stats.total_commits)
    print("Total authors: %s" % stats.total_authors)
    print("Total test files added: %s" % stats.total_test_files_added)
    print("Total files touched: %s" % stats.total_files_changed)
    print("Total lines added (delta): %s" % stats.diff['insertions'])
    print("Total lines deleted (delta): %s" % stats.diff['deletions'])
    print("Total lines added (aggregate): %s" % stats.lines_added)
    print("Total lines deleted (aggregate): %s" % stats.lines_deleted)

    '''
    print("Total files added: %s" % stats.total_files_added)
    print("Total files deleted: %s" % stats.total_files_deleted)
    print("Total files modified: %s" % stats.total_files_modified)
    print("Total test files deleted: %s" % stats.total_test_files_deleted)
    print("Total test files modified: %s" % stats.total_test_files_modified)
    print("diff: %s" % stats.diff)
    '''

if __name__ == '__main__':
    sys.exit(cli())

