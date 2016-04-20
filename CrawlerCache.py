from TorCrawler import TorCrawler
from lxml import etree
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

	# Make a get query and parse the data
	def crawl_get(self, params):
		url = self.form_url(params)
		html = self.parse_html(url)
		return html
			

	# Initialize the cache
	def boot_cache(self, args):
		# Make sure a base url was included
		assert "base_url" in args, "You must include a base url which is a list of substrings."
		assert len(args["base_url"]), "Base url is empty."
		self.base_url = args["base_url"]
		
		# Set the data and req paths
		self.data_path = args["data_path"] if "data_path" in args else "./data.json"
		self.req_path = args["req_path"] if "req_path" in args else "./reqs.json"

		# Set success xpath
		self.success_xpath = args["success_xpath"] if "success_xpath" in args else "//html//title/text()"
		self.fail_xpaths = args["fail_xpaths"] if "fail_xpaths" in args else list()

