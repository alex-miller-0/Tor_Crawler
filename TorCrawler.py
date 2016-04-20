import os
import subprocess
import socket, socks, requests
from lxml import html as HTML
from lxml import etree
from bs4 import BeautifulSoup
import time

# Stem is a module for dealing with tor
from stem import Signal
from stem.control import Controller
from stem.connection import authenticate_none, authenticate_password


# This is a webcrawler that utilizes a Tor client through SOCKS5
# By default, tor runs SOCKS5 through port 9050 on localhost
# Note that the config file for tor can be found in /etc/tor/torrc
#
# Before using this, the user must have tor installed and it must be
# running (e.g. using service tor start)
#
# If rotation is turned on, this client will require the control port
# in tor to be open so that it can send a NEWNYM signal to it, which
# draws a new relay route. Note that in order to send a signal, this client
# first needs to authenticate itself. In /etc/tor/torrc the control port
# can be opened without a password, in which authentication can be done
# without a password. I recommend that you DO NOT DO THIS. Instead, I
# recommend you store some password as an environmental variable, hash it,
# and store the hashed copy in /etc/tor/torrc. The hashed password can be
# generated with:
# 		tor --hash-password "mypassword"
# This will prevent any attackers from sending signals to your tor client.
#
class TorCrawler(object):
	def __init__(self, **kwargs):
		# Number of requests that have been made since last ip change
		self.req_i = 0
		# The number of consecutive requests made with the same ip
		# Defaults to 25 but can be changed
		self.num_requests_with_ip = kwargs["n_requests"] if "n_requests" in kwargs else 25
		# Do we want to use tor?
		self.use_tor = kwargs["use_tor"] if "use_tor" in kwargs else True
		# Do we want to rotate IPs with tor?
		self.rotate_ips = kwargs["rotate_ips"] if "rotate_ips" in kwargs else True
		# Enforce rotation of IPs (if true, redraw circuit until IP is changed)
		self.enforce_rotate = kwargs["enforce_rotate"] if "enforce_rotate" in kwargs else True
		# The threshold at which we can stop trying to rotate IPs and accept the new path
		# This value is capped at 100 because we don't want to kill the tor network
		self.enforce_limit = min(100, kwargs["enforce_limit"]) if "enforce_limit" in kwargs else 3

		# SOCKS params
		self.tor_port = kwargs["socks_port"] if "socks_port" in kwargs else 9050
		self.tor_host = kwargs["socks_host"] if "socks_host" in kwargs else 'localhost'
		# The tor controller that will be used to receive signals
		self.ctrl_port = kwargs["ctrl_port"] if "ctrl_port" in kwargs else 9051
		self.tor_controller = Controller.from_port(port = self.ctrl_port)
		# The control port password
		self.ctrl_pass = kwargs["ctrl_pass"] if "ctrl_pass" in kwargs else None
		self.start_socks()
		self.run_tests()


	# Set our tor client as the proxy server (all future requests will be made through this)
	def start_socks(self):
		socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, self.tor_host, self.tor_port)
		socket.socket = socks.socksocket

	# Parse HTML from a get request
	def parse_html(self, url):
		page = requests.get(url)
		return BeautifulSoup(page.content, 'html.parser')
		
		

	# This will be called to check on my public (broadcasted) ip via tor
	def check_ip(self):
		return requests.get("http://www.icanhazip.com").text[:-2]

	# Attempt to rotate the IP by sending tor client signal NEWNYM
	# Note: this does NOT automatically change the ip; it simply
	# draws a new circuit (i.e. a routing table for your requests/responses).
	# If the number of relays is small, this may indeed return the same IP;
	# that does not mean it is broken!
	# Also note that the default control port is 9051 (different than socks port);
	# this port is used to receive signals.
	def new_circuit(self):
  		if self.ctrl_pass:
  			authenticate_password(self.tor_controller, self.ctrl_pass)
  		else:
  			authenticate_none(self.tor_controller)
  		self.tor_controller.signal(Signal.NEWNYM)

	# Rotate the ip (or, more accurately, redraw the circuit and check if the ip changed)
	def rotate(self):
		# Track the number of times we have attempted rotation and the current ip
		count = 0
		new_ip = None
		# Keep rotating until success
		while count < self.enforce_limit:
			new_ip = self.new_circuit()
			# If the ip didn't change, but we want it to...
			if new_ip == self.ip and self.enforce_rotate:
				print("IP did not change upon rotation. Retrying...")
				time.sleep(2)
				continue
			else:
				self.ip = new_ip
				print("IP successfully rotated. New IP: %s"%(self.ip))
				break

	# Make a get request to a webpage
	# Return the html
	def get(self, url):
		res = self.parse_html(url)
		# Increment counter and check if we need to rotate
		self.req_i += 1
		if self.req_i > self.num_requests_with_ip and self.enforce_rotate:
			self.rotate()
			self.req_i = 0
		return res

	# Setup tests upon initialization
	def run_tests(self):
		if self.use_tor:
			# Check if we are using tor
			print("\nChecking that tor is running...")
			tor_html = self.parse_html("https://check.torproject.org")
			running = tor_html.xpath("//html//title/text()")
			assert "Congratulations" in running[0], "Tor is not running!"
		
			if self.rotate_ips:
				# Redraw the circuit a few times and hope that at least 2 of the
				# external IPs are different
				print("Validating ip rotation...")
				ips = list()
				# Define the number of rotations we will attempt.
				# Note that the testing is different than the actual rotation in
				# that we really only want to run a small number of tests
				num_tests = max(3, self.enforce_limit if self.enforce_limit else 49)
				for i in range(num_tests):
					ips.append(self.check_ip())
					self.new_circuit()
				# If we only got one IP, rotation probably isn't working
				if len(set(ips)) == 1:
					if self.enforce_rotate:
						assert False, "WARNING: Your external IP was the same for %s different relay circuits. You may want to make sure tor is running correctly."%num_tests
					else:
						print("WARNING: Your external IP was the same for %s different relay circuits. You may want to make sure tor is running correctly."%num_tests)
				# Set the IP as the last one
				self.ip = ips[-1]
		print("Ready.\n")
