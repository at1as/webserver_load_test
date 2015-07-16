# web_load_test

Flexible load test utilities for testing your web application.

Load testing is distributed across two seperate tools, `spawn_browsers.py` and `spawn_api_requests.py`. Configuration files are stored in the config/ folder


```bash
config/
	authentication.json
	url_list.json
	browser_totals.json
runner/
	selenium.py
	api_calls.py
```

### Configuration Files

#### authentication.json
#### url_list.json
#### browser_totals.json

### Test Runners

#### Spawn_Browsers.py

This script will use the selenium web driver to spawn desired browsers and visit pages specified in url_list.json. Can spawn both headless browsers, like PhantomJS, and real browsers like Firefox and Chrome.  

Increasing the number of headless phantomjs browsers will allow the computer running this script to spawn more browser sessions (than with firefox, chrome or other browsers), and will ensure all dynamic AJAX content is loaded (dynamic DOM elements, on page load API requests, etc). The server you are testing against should experience roughly the same load with phantomjs as it would with, for instance, a firefox client (as measured by the database and web server)

##### Limitations

However, headless browsers have some limitations:

* In some cases, the phantomJS driver can search for dynamic elements before the page has loaded. Insert wait.until() and time.sleep() if necessary.
* Phantom JS won’t play Flash video, or content that relies upon other plugins. To stress test video, use real browsers by spiking the amount of Firefox, Chrome or other browsers
* With PhantomJS, you will not be able to watch what is happening in real time. For debugging, save screenshots
* PhantomJS has very strict SSL policies. All verification has been disabled in this script.
* Phantomjs has other non-python and non-javascript system dependencies, and some are explicitly required to be 32 bit. Refer to the generated ghostdriver.log for missing dependencies.
* Especially if running on a Mac, but also on Linux, with you may run into a limit on files open on the server. These limits are configurable in your OS


#### Spawn_API_Requests.py

Will issue REST requests using the Python Requests library. This should allow your computer to spawn many more simultaneous requests (perhaps an order of magnitude more than spawn_browsers.py using real browsers). However, for HTML webpages, dynamic elements will not be loaded, which may result in much lower load to the database and web server (if, for instance, every page dynamically loads its images, or portions of the DOM, which would result in even more requests).

##### Limitations

* Especially if running on a Mac, but also on Linux, with many concurrent threads you may run into a limit on threads or processes on number of files open on the server. These limits are configurable in your OS
* Requests has strick SSL policies. All verification has been disabled in the script
