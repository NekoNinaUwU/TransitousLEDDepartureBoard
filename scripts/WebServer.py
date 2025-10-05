from flask import Flask
from flask import request
from datetime import datetime
import pytz
import requests
import xmltodict
import time
import math
import xml.etree.ElementTree as ET
import string
import json

url = "https://api.transitous.org/api/v1/geocode?text="
headers = {'Content-Type': 'application/xml; charset=utf-8'}

station = None

form = """
<form action="" method="get" class="departure-board">
  <div class="departure-board">
    <label for="query">station search: </label>
    <input type="text" name="query" id="query" required />
  </div>
  <div class="departure-board">
    <input type="submit" value="search" />
  </div>
</form>
"""

app = Flask(__name__)

@app.route("/")
def the_one_and_only_endpoint():
    response = form

    global station

    add = request.args.get("add")
    if add is not None:
        print(f"adding {add}")
        station.value += "\n" + add

    remove = request.args.get("remove")
    if remove is not None:
        new = ""
        for i, s in enumerate(station.value.splitlines()):
            if str(i) != remove:
                new += "\n" + s
        if new != "":
            station.value = new

    queryDirty = request.args.get("query")
    if queryDirty is not None:
        queryDirty = queryDirty.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')
        query = ''.join(c for c in queryDirty if c in string.ascii_lowercase or c == ' ')

        print(query)
        response += f'<h3>search for: "{query}"</h3>'

        sex = url + query + "&type=STOP"
        print(sex)
        r = requests.get(url=url + query + "&type=STOP", headers=headers)
        r.encoding = "utf-8"
        print(r.text)
        newr = json.loads(r.text)

        print(newr)



        response += "<ul>"
        for locationresult in newr:
            locationName = ""
            response += "<li>"
            response += f'<p>{locationresult["name"]}</p>'
            for regionthing in locationresult["areas"]:
                locationName += regionthing["name"] + ", "
            response += f'<p>{locationName}</p>'
            ref = locationresult["id"]
            response += f'<a href="?add={ref}">{ref}</a>'
            response += "</li>"
        response += "</ul>"

    response += "<h3>current stations:</h3><ul>"
    for i, s in enumerate(station.value.splitlines()):
        response += "<li>"
        response += f'<p>{s}</p>'
        response += f'<a href="?remove={i}">(X)</a>'
        response += "</li>"
    response += "</ul>"

    return response

def doit(station_value):


    import os
    os.chdir("/")
    print("cwd from webserver is " + os.getcwd())
    print(os.path.exists(os.getcwd()))
    global station
    station = station_value
    app.run(debug=False,host="0.0.0.0")

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0")


