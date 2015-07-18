# web_load_test

Flexible load test utilities for testing your web application. Aims to generalize some aspects of load testing, so that separate applications can use the same script with minimal effort put into reinventing the generic script setup and teardown procedures.

Load testing is distributed across two seperate tools, `spawn_browsers.py` and `spawn_api_requests.py`. Configuration files are stored in the config/ folder


```bash
├── config
│   ├── authentication.json
│   ├── browser_totals.json
│   └── url_list.json
└── runner
    ├── spawn_api_requests.py
    └── spawn_browsers.py
```

### Installation

```bash
$ git clone https://github.com/at1as/web_load_test.git
$ npm install -g phantomjs
$ pip install selenium
```

### Configuration Files
 
#### authentication.json

Note, currently only supports payload authentication.

"browser_url_endpoint", "username", "password" and "submit_buttom" are for selenium testing in spawn_browsers.py. 

"api_auth_endpoint" and "api_auth_payload" are for spawn_requests.py.

* **browser_authentication**
    * enabled => Whether to authenticate before traversing urls [true or false]
    * endpoint => Url endpoint of the browser login page [ex "login"]
* **username**
    * enabled => Whether to supply a username [true or false]
    * value => The username string [ex "user1"]
    * dom_value => The value of the dom key to search for to identify the username field [ex. "username_input"] 
    * dom_element_type => The type of element attribute to search for to identify username field ["id" or "name"]
* **password**
    * enabled => Whether to supply a password [true or false]
    * value => The password string [ex "password1"]
    * dom_value => the value of the element key to search for to identify the password field [ex. "password_input"]
    * dom_element_type => the type of element attribute to search for to identify the password field ["id" or "name"]
* **submit_button**
    * dom_value => the value of the element key to search for to identify [ex. "submit_btn"]
    * dom_element_type => the type of element attribute to search for the identify the submit button ["id" or "name"]
* **api_authentication**
    * enabled => Whether to enable API authentication [true or false]
    * endpoint => The endpoint of the authentication API call (which is not necessary the same as the browser url) [ex. "/authenticate"]
    * request_type => The type of API call needed to authenticate [typically "post", sometimes "put"]
    * payload_as_string => the body the api request must send to authenticate [ex. "{'username':'user1', 'password':'pass1'}"]
    * payload_format => the format of the body ["application/json", "application/xml", "text/plain"]
 
#### url_list.json
   
* protocol => The protocol to use ["http" or "https"]
* url => base url [ex. "www.example.com"]
* endpoints => list of url endpoints to search, [ex. "login", "logout", "stats", "/"]

#### browser_totals.json
   
* Modify the value beside each browser name (as an integer) to match the desired browser breakdown [chrome, headless (phantomJS) and firefox]

```bash
{
  "headless": 1,
  "firefox": 1,
  "chrome": 1
}
```
Above, all browsers will run simultaneously. Enter for quantity to disable one browser. Ensure the selenium webdriver is installed for each which you intend to use, and note that the only supported headless browser right now is PhantomJS (tested with version 1.9.8)

### Test Runners

Run all scripts from the root directory (i.e., `$ python runner/spawn_browsers.py`)
   
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
