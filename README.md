# TorCrawler
Web crawling with IP rotation a la Tor relay redrawing.

This is a little module that allows you to crawl a website anonymously! Does this website limit requests? Rotate your IP! 

# Configuring Tor
Tor configuration is expected to be done outside of this module. Note that this refers to the Tor *client* (i.e. *not* the Tor *browser*. See documentation [here](https://www.torproject.org/docs/documentation.html.en).

Generally, once tor is installed, the configuation file can be found at `/etc/tor/torrc`. SOCKS is configured by default to run on localhost on port 9050, but you can change that if you want. The controller is **not** automatically configured, but the default port is set to 9051 on the line `ControlPort 9051`. Following that line is the parameter `HashedControlPassword`, which I **highly** recommend you set. If you don't, your tor client can be controlled by an attacker unless you have a firewall on port 9051. To generate a tor password, type:
    tor --hash-password mypassword
And stored the hashed result in your `torrc` file. You will be feeding the plaintext version of this password into TorCrawler.

# Rotating IP
To draw a new tor circuit, TorCrawler will use a python packaged called [stem](https://stem.torproject.org/) to send the signal `NEWNYM` to your tor client. Note that this does not *ensure* your external IP will be rotated (there is a chance that the final relay node in your circut will be the same). If you want to make sure it changes, set `enforece_rotate=True` and set some integer value to `enforce_limit`. Note that this limit will be capped at 100 redraws as we do not want to kill the tor network with an infinite loop in case something goes wrong. 


# TorCrawler Usage

To run TorCrawler, initiliaze a `CrawlerCache` loaded with your URL and an xpath along which we should extract data, e.g.

    # The request url
    base_url = ["http://somepage.somewebsite.com?=","&type=somethingelse&foo=bar"]
    # The success xpath
    xpath = "//html//body/div[@id='page']/div[@id='main']/div[@id='content']/div[@class='view']/div[@class='view-content']/div[@class='views-row']/text()"
    # Spin up the crawler
    crawler = CrawlerCache(ctrl_pass=os.environ["TOR_CONT_PASS"], base_url=base_url, success_xpath=xpath, enforce_rotate=False)

Note that the `base_url` is split on each parameter you pass. `crawl_get` takes an array of params (even if length=1). Iterate through whatever parameters you need and parse the HTML (TorCrawler uses Beautiful Soup):

    for i in range(5):
        html = crawler.crawl_get([i])
        for h in html.findAll("div", {"class":"views-row"}):
            first_name, last_name = get_names(h.h3.text)
            email_parsed = h.find("a", {"class":"mailto"})
            email = None
            if email_parsed:
                email = email_parsed.text
                datum = {"first_name": first_name, "last_name": last_name, "email": email}
            if datum["email"]:
                crawler.write_datum(datum)

Data is pickled, as are the requests made, so if the crawler stops it can be resumed at the place it left off. Use the following to resume a CrawlerCache:

    crawler.load_data()
    
# Options
`TorCrawler` and `CrawlerCache` objects can be initialized with the following options. Note that only the `CrawlerCache` should be instantiated from your script (since it inherits from `TorCrawler`), but all of these commands can be passsed to `CrawlerCache`, which executes a super call when constructed.

### TorCrawler Options
  
    # Tor config
    socks_port: <int> (default 9050)                The port tor's socks5 protocol runs out of. Default is 9050 for tor
    socks_host: <str> (default 'localhost')         Your tor host. Default is 'localhost' for tor running locally.
    ctrl_port: <int> (default 9051)                 The port at which tor's controller can be accessed. Default is 9051 for tor
    ctrl_pass: <string> (default None)              (HIGHLY RECOMMENDED) The hashed password for accessing the tor controller
    
    # Crawler config
    n_requests: <int> (default 25)                  Number of consecutive requests that will be made between rotations
    use_tor: <bool> (default True)
    rotate_ips: <bool> (default True)               Ask client to redraw the tor circuit every n_requests
    enforce_rotate: <bool> (default True)           Require the IP change during a rotation cycle (not necessarily enforced: see below)
    enforce_limit: <int> (default 3, max 100)       Max number of times the circuit is redrawn in a rotation event if 

### CrawlerCache Options

    base_url: [<string>, ...]                           The root page of the website you're crawling.
    success_xpath: <string>                             An xpath outlining how to crawl a response HTML page
    data_path: <string> (default "./data.pickle")       Path of the pickled data file
    req_path: <string> (default "./reqs_done.pickle")   Path of the pickled requests dump, i.e. the requests you've completed.
    csv_path: <string> (default "./data.csv")           Path to which the CSV of the data is written
