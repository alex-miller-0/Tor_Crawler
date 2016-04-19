import os
import subprocess
import socket, socks, requests
from lxml import html as HTML

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
class TorCrawler():
	def __init__(self, **kwargs):
		self.tor_port = 9050				
		self.tor_host = 'localhost'			
		# Number of requests that have been made since last ip change
		self.req_since_ip_change = 0		
		# The tor controller that will be used to receive signals
		self.tor_controller = Controller.from_port(port = 9051)
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
		return HTML.fromstring(page.content)

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

	# Setup tests upon initialization
	def run_tests(self):
		
		# Check if we are using tor
		print("Checking that tor is running...")
		tor_html = self.parse_html("https://check.torproject.org")
		running = tor_html.xpath("//html//title/text()")
		assert "Congratulations" in running[0], "Tor is not running!"

		# Redraw the circuit a few times and hope that at least 2 of the
		# external IPs are different
		print("Validating ip rotation...")
		ips = list()
		for i in range(4):
			ips.append(self.check_ip())
			self.new_circuit()
		if len(set(ips)) == 1: print("WARNING: Your external IP was the same for four different relay circuits. You may want to make sure tor is running correctly.")
		print("Ready.\n")


