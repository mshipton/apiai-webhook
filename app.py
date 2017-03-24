#!/usr/bin/env python

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import json
import os
import requests

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)

pound = u'\u00A3'


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    action = req.get("result").get("action")
    if action == "yahooWeatherForecast":
        res = processWeatherRequest(req)
    elif action == "noYouHangUp":
        res = processNoYouHangUpRequest(req)
    elif action == "goDutch":
        res = processGoDutchRequest(req)
    elif action == "marriageAllowanceAges":
        res = processMarriageAllowanceRequest(req)
    elif action == "whatAmICovering":
        res = processWhatAmICoveringRequest(req)        
    else:
        return

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def processWhatAmICoveringRequest(req):
    text = "I am covered in " + req.get("result").get("parameters").get("covering")
    return makeSpeechResponse(text)

def processMarriageAllowanceRequest(req):
    text = ""
    contextOut = []

    yourAge = int(req.get("result").get("parameters").get("your_age"))
    partnerAge = int(req.get("result").get("parameters").get("partner_age"))

    if yourAge >= 82 or partnerAge >= 82:
        text = "Good news! You are elligible for Married Couple's Allowance"
    else:
        text = "Do you or your partner earn less than " + pound + "11000 per year?" 
        contextOut = [{"name":"ask_lower_salary", "lifespan":5}]

    return makeSpeechResponse(text, contextOut) 

def processGoDutchRequest(req):
    # is percentage present?
    # yes -> do calc
    # no -> set context to obtain percent value
    return makeSpeechResponse("work in progress")

def processNoYouHangUpRequest(req):
    counter = 0

    for context in req.get("result").get("contexts"):
        if context.get("name") == "hangup":
            counter = int(context.get("parameters").get("counter"))

    counter += 1
    contextOut = [{"name":"hangup", "lifespan":1, "parameters":{"counter": counter}}]
    
    text = "Ok, you hang up"
    if counter == 2:
        text = "Seriously, hang up"
    elif counter >= 3:
        contextOut = [{"name":"endhangup", "lifespan":1}]
        sound = '<audio src="https://orsilus.com/test/whatami/sad_trombone.wav" />'
        text = "<speak>I've had enough of this!{}</speak>".format(sound)

    return makeSpeechResponse(text, contextOut)


def processWeatherRequest(req):
    baseurl = "https://query.yahooapis.com/v1/public/yql?"
    yql_query = makeYqlQuery(req)
    if yql_query is None:
        return {}
    yql_url = baseurl + urlencode({'q': yql_query}) + "&format=json"
    result = urlopen(yql_url).read()
    data = json.loads(result)
    res = makeWebhookResult(data)
    return res


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "') and u='c'"


def makeWebhookResult(data):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today in " + location.get('city') + ": " + condition.get('text') + \
             ", the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return makeSpeechResponse(speech)


def makeSpeechResponse(speech, contextOut=[]):
    return {
        "speech": speech,
        "displayText": speech,
        "contextOut": contextOut,
        "source": "apiai-webhook"
    }

# def makeSpeechResponse(speech):
#     return {
#         "speech": speech,
#         "displayText": speech,
#         "parameters": {
#             "counter": 1
#         },
#         "contextOut": [{"name":"youHangUp", "lifespan":1, "parameters":{"counter": }}],
#         "source": "apiai-webhook"
#     }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
