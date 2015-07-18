#!/usr/bin/env python

from __future__ import unicode_literals
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import threading
import random
import time
import json

# Developed with Python 2.7.6, PhantomJS 1.9.8
# Tested on OS X and Linux

def find_element_and_fill(browser, selector, value, field_value):
  # Find element by selector (name or id) and value, and send field_value string to element

  if selector == "name":
    WebDriverWait(browser, TIMEOUT).until(EC.presence_of_element_located((By.NAME, value)))
    browser.find_element_by_name(value).send_keys(field_value)
  elif selector == "id":
    WebDriverWait(browser, TIMEOUT).until(EC.presence_of_element_located((By.ID, value)))
    browser.find_element_by_id(value).send_keys(field_value)
  else:
    raise "Invalid Selector type for %s" %value

def find_element_and_click(browser, selector, value):
  # Find element by selector (name or id) and value, and click

  if selector == "name":
    WebDriverWait(browser, TIMEOUT).until(EC.presence_of_element_located((By.NAME, value)))
    browser.find_element_by_name(value).click()
  elif selector == "id":
    WebDriverWait(browser, TIMEOUT).until(EC.presence_of_element_located((By.ID, value)))
    browser.find_element_by_id(value).click()
  else:
    raise "Invalid Selector type for login buttom %s" %value


# Browser Actions
def authenticate(instance):
  print("Browser %s : Authenticating as %s..." %((instance+1), authentication['username']['field_value']))
  
  login_page = "%s://%s/%s" %(url_details['protocol'], url_details['url'], authentication['browser_authentication']['endpoint'])
  browser_instances[instance].get(login_page)

  if authentication['username']['enabled']:
    find_element_and_fill(browser_instances[instance],
                          authentication['username']['dom_element_type'],
                          authentication['username']['dom_value'],
                          authentication['username']['field_value'])

  if authentication['password']['enabled']:
    find_element_and_fill(browser_instances[instance],
                          authentication['password']['dom_element_type'],
                          authentication['password']['dom_value'],
                          authentication['password']['field_value'])

  find_element_and_click( browser_instances[instance],
                          authentication['submit_button']['dom_element_type'],
                          authentication['submit_button']['dom_value'])


def go_to_page(instance, page):
  print("Browser %s : Navigating to %s..." %(instance+1, page))
  browser_instances[instance].get(page)

def teardown(instance):
  print("Browser %s : Quitting browser..." %(instance+1))
  browser_instances[instance].quit()


def worker(instance):
  # The Worker Thread for each webdriver instance

  # Begin by loggin into site if enabled
  if authentication['browser_authentication']['enabled']:
    authenticate(instance)
    time.sleep(AUTH_SLEEP_INTERVAL)
  
  # Visit each page
  for endpoint in url_details['endpoints']:
    full_url = "%s://%s/" %(url_details['protocol'], url_details['url'])
    go_to_page(instance, "%s%s" %(full_url, endpoint))
    time.sleep(PAGE_SLEEP_INTERVAL)
  
  # Clean up browsers after test
  teardown(instance)


# Program Logic
if __name__ == '__main__':

  # How long to wait for an element to appear before throwing a TimeoutException
  TIMEOUT = 5

  # How long to sleep before requesting the next page (to wait for all AJAX elements to load)
  # Alternatively, you can add a WebDriverWait until certain elements are present, but this is hard to generalize
  PAGE_SLEEP_INTERVAL = 1

  # How long to wait after authenticating (to wait for all AJAX elements to load)
  AUTH_SLEEP_INTERVAL = 2


  # Import configured totals for each browser type
  with open('config/browser_totals.json', 'r') as tally_of_browsers:
    browsers = json.load(tally_of_browsers)

  # Import list of endpoints as well as protocol and base url
  with open('config/url_list.json', 'r') as list_of_urls:
    url_details = json.load(list_of_urls)

  # Import authentication details (for sites that require login)
  with open('config/authentication.json', 'r') as login_params:
    authentication = json.load(login_params)
  
  # Intialize empty array to hold browser instances
  browser_instances = []

  # Spawn browser_count browsers
  for browser_type in browsers:
    for x in range(0, browsers[browser_type]):
      
      if browser_type == 'headless':

        # PhantomJS Capabilities for custom timeout length
        capabilities = webdriver.DesiredCapabilities.PHANTOMJS
        capabilities["phantomjs.page.settings.resourceTimeout"] = 1000

        # Arguments to disable all SSL errors for unverified HTTPS connections
        service_args = ['--ignore-ssl-errors=true', '--web-security=false']

        browser_instances.append(webdriver.PhantomJS(desired_capabilities=capabilities, service_args=service_args))
        browser_instances[-1:][0].implicitly_wait(3)
      elif browser_type == 'firefox':
        browser_instances.append(webdriver.Firefox())
      elif browser_type == 'chrome':
        browser_instances.append(webdriver.Chrome())

  # Print test parameters
  print("\nRunning with a total of %s browsers:" %str(len(browser_instances)))
  for browser in browsers: 
    print('\t%s instances of %s browser' %(browsers[browser], browser))
  print '\n'

  # Spawn one worker thread for each function
  # Chrome/PhantomJS/Firefox browsers should be separate subprocesses, so there is likely
  # To be no great advantage for swapping the threading and multiprocessing libraries
  threads = []
  i = 0
  for browser in browser_instances:
    t = threading.Thread(target=worker, args=(i,))
    threads.append(t)
    t.start()
    i += 1

  # Wait for all threads to complete
  for t in threads:
    t.join()

  print("\nAll tests complete\n")
