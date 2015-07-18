#!/usr/bin/env python

import requests
import numpy as np
from multiprocessing import Process, Manager, Lock
import traceback
import signal
import sys
import argparse
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.packages.urllib3.exceptions import InsecurePlatformWarning


###############################################################################
# Simple script for testing site reponse time against concurrent requests     #
# Developed with Python 2.7.6. Tested on OS X and Linux                       #
# Example Usage:                                                              #
#   python spawn_api_requests.py --concurrency 15                             #
###############################################################################



def signal_term_handler(signal, frame):
  # Catch SIGTERM from User
  # If this fails, and processes are left running, execute:
  #   kill -9 `ps -ef | grep -i python | grep -i spawn_api_requests | head -n1 | awk '{ print $2 }'`
  print("Script forced to aborted by user")
  sys.exit()

def status(code):
  # Print Colorized Status Codes (unix OSes only)

  # 2XX HTTP Response (Green)
  if str(code)[0] == "2":
    return "\033[92m" + str(code) + "\033[0m"
  # 4XX/5XX HTTP Response (Red)
  elif str(code)[0] in ["4", "5"]:
    return "\033[91m" + str(code) + "\033[0m"
  # Other HTTP Response (Yellow)
  else:
    return "\033[93m" + str(code) + "\033[0m"

def safe_print(string, lock):
  # Threadsafe version of print
  # print() is threadsafe by default, however newlines are not
  lock.acquire()
  print(string)
  lock.release()


# Method to authenticate and send requests for each worker
def send_http_request(results, times, pages, authentication, timeout, lock, number=1):

  # Optional authentication step
  if authentication['api_authentication']['enabled']:
    try:
      print("\nAuthenticating thread number %s" %(number))

      request_type = authentication['api_authentication']['request_type']
      login_url = "%s://%s/%s" %(url_details['protocol'], url_details['url'], authentication['api_authentication']['endpoint'])
      header = {'Content-Type': authentication['api_authentication']['payload_format']}
      payload = authentication['api_authentication']['payload_as_string']

      r = requests.request(request_type, url=login_url, headers=header, data=payload, verify=False, allow_redirects=True)

    except Exception as e:
      lock.acquire()
      print("Failed to send Authentication Request. Failure Response:")
      traceback.print_exc()
      lock.relase()
      sys.exit()

    if r.status_code in [200, 201]:
      cookies = dict(r.cookies)
      safe_print("Authentication Succeeded\n\tSession Cookie: %s" % (dict(cookies)), lock)
      if sum(1 for _ in r.cookies) == 0:
        safe_print("\t\033[91mWarning:\033[0m Received 2XX status from server, but no Session Cookie was readable. You're probably NOT authenticated", lock)
    else:
      safe_print("Authentication Failure:\n\tStatus: %s\n\tResponse: %s" %(status(r.status_code), r.text), lock)
      sys.exit()
  else:
    cookies = {}

  # After authentication, traverse through each page
  try:
    for page in url_details['endpoints']:

      current_url = "%s://%s/%s" %(url_details['protocol'], url_details['url'], page)
      
      try:
        r = requests.request( 'get', 
                              url=current_url, 
                              cookies=cookies, 
                              verify=False,
                              allow_redirects=True,
                              timeout=(timeout['connect'], timeout['read']))

        times.append(r.elapsed.microseconds)
        results["Valid Response"] += 1
      except requests.exceptions.ReadTimeout as e:
        safe_print("Request Thread %s:\n\t\033[91mRead Timeout!\033[0m No server response in %s seconds" %(number, timeout['read']), lock)
        results["Read Timeout"] += 1
        return
      except requests.exceptions.ConnectTimeout as e:
        lock.acquire()
        safe_print("Request Thread %s:\n\t\033[91mConnect Timeout!\033[0m No server response in %s seconds" %(number, timeout['connect']), lock)
        lock.release()
        results["Connect Timeout"] += 1
        return
      except requests.exceptions.ConnectionError as e:
        safe_print("Request Thread %s:\n\t\033[91mConnection Error!\033[0m %s" %(number, e), lock)
        results["Connection Error"] += 1
        return
      except Exception as e:
        safe_print("Request Thread %s:\n\t\033[91mUnexpected Error!\033[0m %s" %(number, e), lock)
        return

      if not r.status_code == 200:
        safe_print("Failed to get page:\n\tURL: %s\n\tStatus: %s" %(current_url, status(r.status_code)), lock)
      else:
        if r.history:
          for redirect in r.history:
            safe_print("Request Thread %s:\n\tStatus: %s\n\tTime: %s\n\tRedirects:\n\t\t%s : %s" %( number, status(r.status_code), float(r.elapsed.microseconds) / 1000000,
                                                                                                    status(redirect.status_code), redirect.url), 
                                                                                                    lock)
          safe_print("\tFinal Destination:\n\t\t%s : %s" %(status(r.status_code), r.url), lock)
        else:
          safe_print("Request Thread %s:\n\tURL: %s\n\tStatus: %s\n\tTime: %s" %(number, r.url, status(r.status_code), float(r.elapsed.microseconds) / 1000000), lock)

  except KeyboardInterrupt:
    sys.exit()



if __name__ == "__main__":

  # Disable all SSL warnings
  try:
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
  except:
    pass

  # Catch Sigterm from User
  signal.signal(signal.SIGTERM, signal_term_handler)

  # Globals
  subprocesses = []
  count   = 0
  manager = Manager()
  lock    = manager.Lock()
  times   = manager.list()
  results = manager.dict()
  results["Valid Response"]   = 0
  results["Connection Error"] = 0
  results["Read Timeout"]     = 0
  results["Connect Timeout"]  = 0

  # Import list of URLs:
  #   protocol, base url, and list of endpoints
  with open('config/url_list.json', 'r') as url_endpoints:
    url_details = json.load(url_endpoints)

  # Import  Authentication Details:
  #   username, password, url, request type and url endpoint
  with open('config/authentication.json', 'r') as login_params:
    authentication = json.load(login_params)

  # Parse User Command Line Arguments
  parser = argparse.ArgumentParser(description='Spawn multiple HTTP request threads to request specified URL.')
  parser.add_argument("--concurrency", dest="concurrency", type=int, default=1, required=False, help='number of users simultaneously requesting pages (ex. --concurrency 15)')
  args = parser.parse_args()
  user_args = vars(args)

  # Configurable Parameter Defaults
  concurrency = user_args['concurrency']
  timeout     = {"read": 5, "connect": 5}


  # Send Parallel URL Requests
  # Note: Number of worker processes is bound by host
  #   Too many subprocesses yields OSOSError: [Errno 35] Resource temporarily unavailable
  #   This should be configurable on your OS
  print("\nSpawning: \n\t%s subprocesses for %s simultaneous requests of page" %(concurrency, concurrency))

  # Spawn a process for every request instance
  for x in range(0,concurrency):
    count += 1
    p = Process(target=send_http_request, args=(results, times, url_details, authentication, timeout, lock, count,))
    subprocesses.append(p)
    p.start()

  # Wait for all processes to complete
  for subprocess in subprocesses:
      subprocess.join()

  # Calculate average response time
  # Average Time in seconds
  avg_time = "N/A"
  if len(times) > 0:
    avg_time = float(sum(times)/len(times))/1000000

  # Print Results to Console
  # JW: TODO clean these up so they don't throw exceptions for empty data setsg
  print("\nAll Requests Sent:")
  print("\tValid Response: %s" %(results["Valid Response"]))
  print("\tConnection Error: %s" %(results["Connection Error"]))
  print("\tRead Timeout: %s" %(results["Read Timeout"]))
  print("\tConnect Timeout: %s\n" %(results["Connect Timeout"]))

  print("Average Response Time:\n\t%s seconds" %(str(avg_time)))
  print("Minimum Response Time:\n\t%s seconds" %(str(float(min(times))/1000000)))
  print("Maximum Response Time:\n\t%s seconds" %(str(float(max(times))/1000000)))
  print("Median Response Time:\n\t%s seconds" %(np.median(times)/1000000))
  print("Standard Deviation:\n\t%s seconds\n" %(np.std(times)/1000000))

