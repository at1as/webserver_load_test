#!/usr/bin/env python

import requests
import numpy as np
from multiprocessing import Process, Manager, Lock
import traceback
import signal
import sys
import argparse
import json


###############################################################################
# Simple script for testing site reponse time against concurrent requests     #
# Developed with Python 2.7.6. Tested on OS X and Linux                       #
# Example Usage:                                                              #
#   python spawn_api_requests.py --concurrency 15                             #
###############################################################################


# Catch SIGTERM from User
# If this fails, and processes are left running, execute:
#   kill -9 `ps -ef | grep -i python | grep -i spawn_api_requests | head -n1 | awk '{ print $2 }'`
def signal_term_handler(signal, frame):
  print("Script forced to aborted by user")
  sys.exit()

# Print Colorized Status Codes (unix OSes only)
def status(code):
  # 2XX HTTP Response (Green)
  if str(code)[0] == "2":
    return "\033[92m" + str(code) + "\033[0m"
  # 4XX/5XX HTTP Response (Red)
  elif str(code)[0] in ["4", "5"]:
    return "\033[91m" + str(code) + "\033[0m"
  # Other HTTP Response (Yellow)
  else:
    return "\033[93m" + str(code) + "\033[0m"


# Method to authenticate and send requests for each worker
def send_http_request(results, times, pages, authentication, lock, timeout, number=1):

  # Optional authentication step
  if authentication['api_authentication']['enabled']:
    try:
      print("\nAuthenticating thread number %s" %(number))
      r = requests.request( 
                            authentication['api_authentication']['request_type'],
                            url="%s://%s/%s" %(url_details['protocol'], url_details['url'], authentication['api_authentication']['endpoint']),
                            json=authentication['api_authentication']['payload_as_string'],
                            verify=False
                            )
    except Exception as e:
      print("Failed to send Authentication Request. Failure Response:")
      traceback.print_exc()
      sys.exit()

    if r.status_code in [200, 201]:
      cookies = dict(r.cookies)
      print("Authentication Succeeded\n\tSession Cookie: %s" % (dict(cookies)))
      if not cookies.has_key('sessionId'):
        print("\t\033[91mWarning:\033[0m Received 2XX status from server, but no Session Cookie was returned. You're probably NOT authenticated")
    else:
      print("Authentication Failure:\n\tStatus: %s\n\tResponse: %s" %(status(r.status_code), r.text))
      sys.exit()
  else:
    cookies = {}

  # After authentication, traverse through each page
  try:
    for page in url_details['endpoints']:
      lock.acquire()
      try:
        r = requests.request( 'get', 
                              url="%s://%s/%s" %(url_details['protocol'], url_details['url'], page), 
                              cookies=cookies, 
                              timeout=(timeout['connect'], timeout['read']),
                              verify=False
                              )
        times.append(r.elapsed.microseconds)
        results["Valid Response"] += 1
      except requests.exceptions.ReadTimeout as e:
        print("Request Thread %s:\n\t\033[91mRead Timeout!\033[0m No server response in %s seconds" %(number, timeout['read']))
        results["Read Timeout"] += 1
        return
      except requests.exceptions.ConnectTimeout as e:
        print("Request Thread %s:\n\t\033[91mConnect Timeout!\033[0m No server response in %s seconds" %(number, timeout['connect']))
        results["Connect Timeout"] += 1
        return
      except requests.exceptions.ConnectionError as e:
        print("Request Thread %s:\n\t\033[91mConnection Error!\033[0m %s" %(number, e))
        results["Connection Error"] += 1
        return
      except Exception as e:
        print("Request Thread %s:\n\t\033[91mUnexpected Error!\033[0m %s" %(number, e))
        return

      if not r.status_code == 200:
        print("Failure to get page:\n\tURL: %s\n\tStatus: %s\n\tResponse: %s" %(page, status(r.status_code), r.text))
      else:
        if r.history:
          for redirect in r.history:
            print("Request Thread %s:\n\tStatus: %s\n\tTime: %s\n\tRedirects:" %(number, status(r.status_code), float(r.elapsed.microseconds) / 1000000))
            print("\t\t%s : %s" %(status(redirect.status_code), redirect.url))
          print("\tFinal Destination:\n\t\t%s : %s" %(status(r.status_code), r.url))
        else:
          print("Request Thread %s:\n\tURL: %s\n\tStatus: %s\n\tTime: %s" %(number, r.url, status(r.status_code), float(r.elapsed.microseconds) / 1000000))
      lock.release()
  except KeyboardInterrupt:
    sys.exit()



if __name__ == "__main__":

  # Disable SSL warnings
  requests.packages.urllib3.disable_warnings()

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

