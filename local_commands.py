import os
import subprocess
import shlex
import asyncio
from passbacklib import resolve, Resolver, autoresolve
from dataclasses import dataclass

# pbcopy just passes the input from the remote machine to the local machine
autoresolve("pbcopy", pipe_input=True)


class FileToClipboard(Resolver, name="pbfcopy", file_input="$1"):
    """Takes one argument. Copy the contents of the provided file to the clipboard

    pbfcopy path/to/file
    is equivalent to
    cat path/to/file | pbcopy

    """

    def _call(self):
        return self.pass_to("pbcopy")


class OpenGitWeb(Resolver, name="gitweb"):
    """ Open the url for a git repository locally """

    git_url: str = "$(git remote get-url origin)"

    def _call(self):
        http_url = self.git_url.replace("ssh://", "http://")
        if http_url.endswith(".git"):
            http_url = http_url[:-4]
        return self.pass_to("open", http_url)


class OpenUrl(Resolver, name="webme"):
    """ Requires a single argument. Opens the url provided locally """

    def _call(self, url):
        subprocess.run(f"open {url}", shell=True)
        return f"Opened {url}\n"


# class SayMyName(Resolver, name='speak'):
#    host: str="${HOSTNAME:-${HOST}}"
#
#    def _call(self):
#        subprocess.run(["say", self.host])
#
