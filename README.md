# TorCrawler
Web crawling with IP rotation a la Tor relay redrawing.

Sometimes you need to crawl a directory and sometimes that means making a lot of requests. You may want to brute force it and run the risk of getting your IP blacklisted (just go to a coffee shop, right?), but probably not. You probably want to deploy the crawler on an EC2 instance and forget about it. If so, this one's for you.

# Usage
**IMPORTANT:** This module will only work with Python 3, due to problems arising from cross-usage of sockets with the stem module.


# Tor
[Tor](https://www.torproject.org/) is a wonderful piece of software that draws a route between your computer and the internet. This route (or circuit) is composed of a series of Tor relays (a.k.a. nodes), which are proxy servers running Tor and routing traffic between Tor clients (e.g. your computer) and the internet. Once the circuit is drawn, a request is made from your machine which is encrypted N times, where N is the number of nodes in your circuit. As the request reaches each node, it decrypts the outermost layer of encryption and passes the traffic to the next relay. The final relay makes the request to the server, recieves the response, and shuttles the traffic (again encrypted N times) back along the circuit it came from. This process is sometimes called "onion routing" because each layer of encryption is "peeled back" at each subsequent node, sort of like an onion:

![onion routing](http://www.extremetech.com/wp-content/uploads/2015/07/tor-onion.png)

Once you boot up Tor, it will automatically configure a circuit and your proxy IP will be the last node in the circuit (a.k.a. the exit node). If you want to use Tor in your every day browsing, you can check out their neat Tor browser, but do keep in mind that there are, as of writing this, only about 7000 Tor nodes in the world and that the point of the network is to, e.g., protect free speech of people in totalitarian regimes so please don't clog up the network by downloading the last season of Game of Thrones (it would be slow anyway). Also note that Tor is technically anonymous browsing, but this is a very grey area, especially if exit nodes are compromised or you are browsing in an identifiable way. If you are concerned with anonymous browsing, don't use the same circuit to repeatedly Google yourself and log in to your bank account.

## Configuring Tor
Tor is fairly straightforward to set up and run as a proxy server for web requests. First, [download](https://www.torproject.org/projects/torbrowser.html.en) the Tor browser. This will install Tor alongside the browser (we will only be using the client, not the browser). This guide will assume you are on a UNIX system. The config file is located at `/etc/tor/torrc`. Tor can be started as a service using `service tor start`. Before proceeding, we need to check on two configurations for our crawler:

### SOCKS5
Our crawler will make requests by proxy through Tor via SOCKS5. By default, Tor will boot running SOCKS5 on `localhost` via `port 9050`. You can change these settings if you need to.

### Tor Controller
The Tor service can be sent commands via the control port. The command we will use for the crawler is called `NEWNYM`, which tells Tor to redraw the circuit. Note that this does not *always* mean your circuit's exit node will have a new IP (Tor could choose a different route, but keep the exit node in place), so we may need to call NEWNYM multiple times to get a fresh IP. The controller is *not* automatically configured because opening it makes you susceptible to attacks. For this reason, we will only want to open the port once we have a hashed password in place. To generate a tor-compatible hashed password, run:

    tor --hash-password mypassword

And save the hashed password in your `torrc` file on the line that begins with `HashedControlPassword`. Also be sure to uncomment the line that says `ControlPort 9051`. When sending a command to the tor controller, you will use the plain text version of this hashed password; I recommend saving it as an environmental variable in your bash profile.

## TorCrawler Usage

To run TorCrawler, initiliaze a `CrawlerCache` loaded with your URL and an xpath along which we should extract data, e.g.

    # The request url
    base_url = ["http://somepage.somewebsite.com?=","&type=somethingelse&foo=bar"]
    # The success xpath
    xpath = "//html//body/div[@id='page']/div[@id='main']/div[@id='content']/div[@class='view']/div[@class='view-content']/div[@class='views-row']/text()"
    # Spin up the crawler
    crawler = CrawlerCache(ctrl_pass=os.environ["TOR_CONT_PASS"], base_url=base_url, success_xpath=xpath, enforce_rotate=False)

Note that the `base_url` is split on each parameter you pass. `crawl_get` takes an array of params (even if length=1). Iterate through whatever parameters you need and parse the HTML (TorCrawler uses Beautiful Soup). Here is an example:

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

Both response data and made requests are pickled so if the crawler stops it can be resumed at the place it left off. Use the following to resume a CrawlerCache:

    crawler.load_data()

## Options
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
