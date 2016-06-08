"""
Run with py.test-3 (TorCrawler requires python3)
"""

# Modules required:
# PySocks, bs4, stem, pytest-3

import sys
import os
import pytest
import subprocess
sys.path.append("./../src")
from TorCrawler import TorCrawler
import time


def startTor():
    subprocess.call(["sudo service tor start"], shell=True)

def stopTor():
    subprocess.call(["sudo service tor stop"], shell=True)

def test_env_var_exists():
    """Test that the environment variable containing controller pswd exists."""
    fail_msg = "Please assign an environment variable called 'TOR_CTRL_PASS' \
    with your plaintext Tor controller password. The hashed password should \
    be set as 'HashedControlPassword' in your torrc file."
    assert "TOR_CTRL_PASS" in os.environ, fail_msg

def test_setup():
    """
    Test setup of TorCrawler.

    There are some major issues with testing multiple Controllers, i.e.
    testing multiple instances of TorCrawler.

    For some reason, when a stem Controller is instantiated and connects
    via SOCKS to my control port, that port remains in use even after the
    Controller instance is killed or otherwise dies. This means that in the
    thread of py.test-3, I can't spin up new TorCrawlers which is a major pain.

    For now, the workaround will be to throw a successful TorCrawler up to
    a global variable, but I can work on a multithreaded solution later (not
    sure if that would even work).
    """
    stopTor()
    time.sleep(1)

    # Should fail if Tor is not running.
    with pytest.raises(EnvironmentError):
        c = TorCrawler()

    # Boot Tor
    startTor()
    time.sleep(1)
    c4 = TorCrawler(test_rotate=True)

    global TOR_CRAWLER
    TOR_CRAWLER = c4

def test_new_circuit():
    old_ip = TOR_CRAWLER.ip
    TOR_CRAWLER.rotate()
    assert old_ip != TOR_CRAWLER.check_ip(), "IP rotation failed."
