from TorCrawler import TorCrawler
from lxml import etree
import json
import pickle
import os.path
import numpy as np
# Load this cache to crawl e.g. a directory with TorCrawler.
# 
# The idea is that you will set up a directory and a crawl script
# which will iterate through a bunch of combinations of requests
# and from each request will build a set of data entries.
# For example, if you are crawling a directory of people, search
# combinations of two characters for first and last name and process
# the hits. As you go along, only add unique people to the set and
# save it between requests.
# 
# This will also save the requests you've made so if you need to kill
# the process, you will not lose your place
class CrawlerCache(TorCrawler):
	def __init__(self, **kwargs):
		# Initialize the TorCrawler with a super call
		super(CrawlerCache, self).__init__(**kwargs)

		# A collection of requests that have been made
		self.req_done = list()
		# A collection of all requests to be made (superset of req_done)
		self.req_planned = list()
		# The data scraped
		self.data = list()

		# The xpath of the loaded webpage that contains all of the data you want
		# e.g. "//html//title/text()"
		self.success_xpath = None
		# A list of failure xpaths
		self.fail_xpaths = None

		# Data path to save information
		self.data_path = None
		# Path to store finished requests
		self.req_path = None

		# Base request url; this is actually a list of substrings split
		# by locations where params are concatenated
		self.base_url = list()

		# Boot the crawler
		self.boot_cache(kwargs)


	# Form a request url given n substrings in a base url and n-1 params 
	# Note: base url may contain an empty string at the end
	def form_url(self, params):
		assert len(params) == len(self.base_url)-1, "Incorrect number of params in request. URL should have %s params."%(len(self.base_url)-1)
		url = self.base_url[0]
		for i in range(1, len(self.base_url)):
			url += params[i-1]
			url += self.base_url[i]
		return url

	# Pickle iterator
	# This can either return a list of data from the pickle file or None
	# It will return None if we pass in the "check" kwarg, which tells this function
	# to check if a piece of data already exists in the pickle file
	def get_pickle(self, f, **kwargs):
		data = list()
		check = kwargs["check"] if "check" in kwargs else None
		while True:
			try: 
				# Load each line of the pickle file
				datum = pickle.load(f)
				# If we want to check for an existing datum and we find it, return None
				if check:
					if datum["params"] == check["params"]: 
						return None
				data.append(datum)
			except EOFError as err:
				return data


	# Create a generator for loading a pickle file
	def pickleLoadGenerator(self, f):
		try:
			while True:
				yield pickle.load(f)
		except EOFError:
			pass


	# Check if the request has already been made
	# If the file exists, create a generator to loop through the pickle file data
	# and check if the datum passed in is in the file
	def check_request_done(self, datum):
		if os.path.isfile(self.req_path):
			with open(self.req_path, 'rb+') as f:
				for d in self.pickleLoadGenerator(f):
					if d["params"] == datum["params"]: return True
			return False
			f.close()


	# Before making a request, save that it has been performed to a pickle file
	# if it is not already in the pickle file.
	# If it IS in the file, return None and don't make the request
	def save_req_done(self, datum):
		check_done = self.check_request_done(datum)
		if not check_done:
			with open(self.req_path, 'ab+') as f_out:
				pickle.dump(datum, f_out)
				return datum
			f_out.close()
		return None


	# Add a set of params to a list of requests made 
	def add_req_done(self, params):
		self.req_done.append(params)
		return self.save_req_done({"params": params})


	# Load data from file
	def load_data(self):
		with open(self.data_path, 'rb+') as f:
			for d in self.pickleLoadGenerator(f):
				self.data.append(d)

	# Filter out redundant data
	# First, convert self.data (a list of dicts) to a list of hashable objects (strings)
	# then run set() and recast back to dicts
	def clean_data_set(self):
		set_data = set(list(map(lambda x: json.dumps(x), self.data)))
		self.data = None
		self.data = list(map(lambda y: json.loads(y), set_data))

	# Write a datum to the data file
	def write_datum(self, datum):
		with open(self.data_path, 'ab+') as f:
			pickle.dump(datum, f)


	# Make a get query and parse the data
	def crawl_get(self, params):
		# Form the URL
		url = self.form_url(params)
		
		# Add the request to the list
		req = self.add_req_done(params)

		# Return a BeautifulSoup object with the data in an html string
		# Often, this will be a series of <div> elements (wrapped in a single
		# long html string)
		soup = self.parse_html(url)
		return soup
	



	# Initialize the cache
	def boot_cache(self, args):
		# Make sure a base url was included
		assert "base_url" in args, "You must include a base url which is a list of substrings."
		assert len(args["base_url"]), "Base url is empty."
		self.base_url = args["base_url"]
		
		# Set the data and req paths
		self.data_path = args["data_path"] if "data_path" in args else "./data.pickle"
		self.req_path = args["req_path"] if "req_path" in args else "./reqs_done.pickle"

		# Set success xpath
		self.success_xpath = args["success_xpath"] if "success_xpath" in args else "//html//title/text()"
		self.fail_xpaths = args["fail_xpaths"] if "fail_xpaths" in args else list()

