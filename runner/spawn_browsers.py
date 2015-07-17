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


# Browser Actions
def authenticate(instance):
  print("Browser %s : Authenticating as %s..." %((instance+1), user['name']))
  
  login_page = "%s://%s/%s" %(url_details['protocol'], url_details['url'], authentication['browser_url_endpoint'])
  browser_instances[instance].get(pages[login_page])
  
  #wait = WebDriverWait(browser_instances[instance], 10)
  #wait.until(EC.invisibility_of_element_located((By.NAME, 'username')))
  #print browser_instances[instance].page_source.encode("utf-8")

  browser_instances[instance].find_element_by_name('username').send_keys(user['name'])
  browser_instances[instance].find_element_by_id('password').send_keys(user['password'])
  browser_instances[instance].find_element_by_id("login").click()

def go_to_page(instance, page):
  print("Browser %s : Navigating to %s..." %(instance+1, page))
  browser_instances[instance].get(page)

def teardown(instance):
  print("Browser %s : Quitting browser..." %(instance+1))
  browser_instances[instance].quit()


# Worker Thread
def worker(instance):

  # Begin by loggin into site if enabled
  if authentication['enabled']:
    authenticate(instance)
  
  # Visit each page
  for endpoint in url_details['endpoints']:
    full_url = "%s://%s/" %(url_details['protocol'], url_details['url'])
    go_to_page(instance, "%s%s" %(full_url, endpoint))
  
  # Clean up browsers after test
  teardown(instance)


# Program Logic
if __name__ == '__main__':

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
      
      if browser_type == 'phantom':
        capabilities = webdriver.DesiredCapabilities.PHANTOMJS
        capabilities["phantomjs.page.settings.resourceTimeout"] = 1000
        browser_instances.append(webdriver.PhantomJS(desired_capabilities=capabilities, service_args=['--ignore-ssl-errors=true', '--web-security=false']))
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
