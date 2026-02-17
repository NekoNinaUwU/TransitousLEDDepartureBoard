import WebServer

from threading import Thread
import math
import xml.etree.ElementTree as ET
from multiprocessing import Process, Value, Manager
import ctypes 
from datetime import datetime, timedelta
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics, FrameCanvas
import pytz
import requests
import xmltodict
import time
import json
import csv

url = "https://api.transitous.org/api/v5/stoptimes?stopId="
headers = {'Content-Type': 'application/xml'}

## Available: kvv, kvb
displayDesign = "kvv"

stopPoints = ["de-DELFI_de%3A08212%3A3%3A3%3A3","de-DELFI_de:08212:1001:1:1"]
track = ""
#stopPoint = f"de:08212:3{track}"

weatherChoice = True

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 64
options.cols = 128

current_hour = datetime.now().hour
print(current_hour)
if current_hour >= 22 or current_hour < 6:
    options.brightness = 15
    print("dunkel")
else:
    options.brightness = 80
#options.pixel_mapper_config = "Rotate:90"
options.chain_length = 2
options.hardware_mapping = 'regular'
options.gpio_slowdown = 5
#options.parallel = 2
#options.pwm_dither_bits = 2

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()
font = graphics.Font()

if displayDesign == "kvv":
    font.LoadFont("fonts/kvv-custom-14.bdf")
    textColor = graphics.Color(255, 120, 0)
elif displayDesign == "kvb":
    font.LoadFont("fonts/7x13.bdf")
    textColor = graphics.Color(255, 255, 255)
else:
    font.LoadFont("fonts/7x13.bdf")
    textColor = graphics.Color(255, 120, 0)

alleStorung = ""

current_deps = []

def get_weather(lat, lon):
    weatherURL = "https://api.open-meteo.com/v1/forecast"
    weatherParams = {
	"latitude": lat,
	"longitude": lon,
	"current": ["temperature_2m", "weather_code"],
	"forecast_days": 1,
}
    
    weatherResponse = requests.get(weatherURL, params=weatherParams)
    weatherData = weatherResponse.json()
    #print(weatherData)

    weatherTemp = weatherData["current"]["temperature_2m"]
    weatherCode = weatherData["current"]["weather_code"]
    return weatherTemp, weatherCode



def get_departures(stopPoint):
    currentTime = (datetime.now()+timedelta(hours=0)).astimezone(tz=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    currentTimestamp = datetime.now().astimezone(tz=pytz.utc).timestamp()
    r = requests.get(url=url + stopPoint + "&n=20", headers=headers)
    r.encoding = "utf-8"
    newr = json.loads(r.text)

    shortTime = datetime.now().strftime("%H:%M")
    shortDate = datetime.now().strftime("%d.%m.%y")

    deps = []

    #print(newr)
    stationName = newr["place"]["name"]

    if displayDesign == "kvv":
        for stopeventresult in newr["stopTimes"]:
            #print(stopeventresult)
            place = stopeventresult["place"]
            #tripto = stopeventresult["tripto"]
            LiveDeparture = None
            if stopeventresult["realTime"] == True:
                LiveDeparture = place["departure"]
                PrintLiveConv = datetime.fromisoformat(LiveDeparture).astimezone(pytz.timezone("Europe/Berlin"))
                # PrintLive = PrintLiveConv.strftime("%H:%M")
                LiveAb = PrintLiveConv.timestamp() - currentTimestamp
                if LiveAb > 600:
                    PrintLive = f"{PrintLiveConv.hour:02}:{PrintLiveConv.minute:02}"
                else:
                    minAb = math.floor(LiveAb / 60)
                    if minAb <= 0:
                        PrintLive = "sofort"
                    else:
                        PrintLive = f"in {math.floor(LiveAb / 60)} min"
                UnliveDeparture = ""
                PrintUnlive = "/"
            else:
                UnliveDeparture = place["scheduledDeparture"]
                PrintUnliveConv = datetime.fromisoformat(UnliveDeparture).astimezone(pytz.timezone("Europe/Berlin"))
                PrintUnlive = PrintUnliveConv.strftime("%H:%M")
                PrintLive = "/"
            LineNumber = stopeventresult["routeShortName"]
            
            if "FDS Hbf" in stopeventresult["headsign"]:
                ShortDest = "Freudenstadt Hbf"
            elif "Hauptbahnhof (oben)" in stopeventresult["headsign"]:
                ShortDest = "Stuttgart Hbf"
            else:
                ShortDest = stopeventresult["headsign"]

            if "DB Fernverkehr AG" in stopeventresult["agencyName"]:
                LineNumber = stopeventresult["displayName"]

            if "RNV" in LineNumber:
                LineNumber = LineNumber.replace("RNV","")

            # if "(Umleitung)" in FullDestination:
            #     ShortDest = FullDestination.split("(Umleitung)")[0]
            # else:
            #     ShortDest = FullDestination
            # if "> SEV ab" in FullDestination:
            #     ShortDest = FullDestination.split(" ab")[0]

            Cancelled = "/"
            try:
                if place["cancelled"]: #or place["CallAtStop"]["NotServicedStop"] == "true"
                    Cancelled = "Ausfall"
            except:
                pass
            
            # if "Attribute" in tripto:
            #     try:
            #         GetStepfree = tripto["Attribute"]["Text"]["Text"]
            #     except:
            #         GetStepfree = ""

            #print(GetStepfree)

            #     if "Niederflurwagen" in GetStepfree or "Stufenloses" in GetStepfree:
            #         Stepfree = "¤"
            #         #Stepfree = "£"
            #     else:
            #         Stepfree = ""

            # else:
            #     Stepfree = ""

            BestDeparture = ""
            if LiveDeparture is not None:
                BestDeparture = LiveDeparture
            else:
                BestDeparture = UnliveDeparture

            DepartureString = ""
            if PrintLive != "/":
                liveDep = PrintLive
                unliveDep = ""
            else:
                unliveDep = PrintUnlive
                liveDep = ""

            agencyName = stopeventresult["agencyName"]
            agencyId = stopeventresult["agencyId"]
            scheduledDep = place["scheduledDeparture"]

            # Get line color info once per departure
            try:
                routeColor = stopeventresult["routeColor"]
            except:
                routeColor = "ff7800"
            #routeTextColor = stopeventresult["routeTextColor"]

            try:
                routeTextColor = stopeventresult["routeTextColor"]
            except:
                routeTextColor = "ffffff"

            try:
                lat = place["lat"]
                lon = place["lon"]
                if weatherChoice:
                    weatherTemp, weatherCode = get_weather(lat, lon)
                    #weatherIcon = get_weather_icon(weatherCode)
            except:
                lat = None
                lon = None
                weatherTemp = None
                weatherCode = None

            deps.append({
                "shortTime": shortTime,
                "stationName": stationName,
                "liveDep": liveDep,
                "unliveDep": unliveDep,
                "depTimestamp": BestDeparture,
                "scheduledDep": scheduledDep,
                "agencyId": agencyId,
                "agencyName": agencyName,
                "line": LineNumber,
                "destination": ShortDest,
                "cancelled": Cancelled,
                "routeColor": routeColor,
                "routeTextColor": routeTextColor,
                "weatherTemp": weatherTemp,
                "weatherCode": weatherCode
            })

    elif displayDesign == "kvb":
        shortTime = datetime.now().strftime("%H:%M") + " Uhr"
        for stopeventresult in newr["stopTimes"]:
            #print(stopeventresult)
            place = stopeventresult["place"]
            #tripto = stopeventresult["tripto"]
            LiveDeparture = None
            if stopeventresult["realTime"] == True:
                LiveDeparture = place["departure"]
                PrintLiveConv = datetime.fromisoformat(LiveDeparture).astimezone(pytz.timezone("Europe/Berlin"))
                # PrintLive = PrintLiveConv.strftime("%H:%M")
                LiveAb = PrintLiveConv.timestamp() - currentTimestamp
                PrintLive = f"{math.floor(LiveAb / 60)} Min"
                minAb = math.floor(LiveAb / 60)
                if minAb <= 0:
                    PrintLive = "Sofort"
                UnliveDeparture = ""
                PrintUnlive = "/"
            else:
                UnliveDeparture = place["scheduledDeparture"]
                PrintUnliveConv = datetime.fromisoformat(UnliveDeparture).astimezone(pytz.timezone("Europe/Berlin"))
                PrintUnlive = f"{math.floor((PrintUnliveConv.timestamp() - currentTimestamp) / 60)} Min"
                if math.floor((PrintUnliveConv.timestamp() - currentTimestamp) / 60) <= 0:
                    PrintUnlive = "Sofort"
                PrintLive = "/"
            
            LineNumber = stopeventresult["routeShortName"]
            ShortDest = stopeventresult["headsign"]


            Cancelled = "/"
            try:
                if place["cancelled"]:
                    Cancelled = "Ausfall"
            except:
                pass


            BestDeparture = ""
            if LiveDeparture is not None:
                BestDeparture = LiveDeparture
            else:
                BestDeparture = UnliveDeparture

            DepartureString = ""
            if PrintLive != "/":
                liveDep = PrintLive
                unliveDep = ""
            else:
                unliveDep = PrintUnlive
                liveDep = ""

            agencyName = stopeventresult["agencyName"]
            agencyId = stopeventresult["agencyId"]
            scheduledDep = place["scheduledDeparture"]
            
            try:
                track = place["track"]
            except:
                track = ""
            # Get line color info once per departure
            try:
                routeColor = stopeventresult["routeColor"]
            except:
                routeColor = "ff7800"
            #routeTextColor = stopeventresult["routeTextColor"]

            try:
                routeTextColor = stopeventresult["routeTextColor"]
            except:
                routeTextColor = "ffffff"

            try:
                lat = place["lat"]
                lon = place["lon"]
                if weatherChoice:
                    weatherTemp, weatherCode = get_weather(lat, lon)
                    #weatherIcon = get_weather_icon(weatherCode)
            except:
                lat = None
                lon = None
                weatherTemp = None
                weatherCode = None

            deps.append({
                "shortTime": shortTime,
                "shortDate" : shortDate,
                "stationName": stationName,
                "liveDep": liveDep,
                "unliveDep": unliveDep,
                "depTimestamp": BestDeparture,
                "scheduledDep": scheduledDep,
                "track" : track,
                "agencyId": agencyId,
                "agencyName": agencyName,
                "line": LineNumber,
                "destination": ShortDest,
                "cancelled": Cancelled,
                "routeColor": routeColor,
                "routeTextColor": routeTextColor,
                "weatherTemp": weatherTemp,
                "weatherCode": weatherCode
            })

    global current_deps
    current_deps = sorted(deps, key=lambda item: item["depTimestamp"])

manager = Manager()
stop_point_value = manager.Value(ctypes.c_wchar_p, "de-DELFI_de%3A08212%3A3%3A3%3A3\nde-DELFI_de:08212:1001:1:1")
web_server_process = Process(target=WebServer.doit,args=[stop_point_value])
print("starting web server")
web_server_process.start()


get_departures(stopPoints[0])
stop_index_counter = 0
cycle_count = 0
update_counter = 0
updateInterval = 50
zeilen = ""
pos = 0
posVert = 0
#alleStorung = "Bitte beachten Sie das geänderte Linienkonzept der Phase 420 Muahaa  "
lineColorText = graphics.Color(255, 255, 255)
last_pause_pos = None
pause_counter = 0
pause_duration = 5  # seconds
pause_start_time = time.time()  # Start pause immediately
is_paused = True                # Start in paused state
scrolling_up = False            # New flag for scroll direction
end_pause = False               # New flag for end pause
end_pause_start = None          # Timestamp for end pause

#TO DO: Line shapes, lol

def hex_to_rgb(hex):
  return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))


while True:
    if displayDesign == "kvv":
        canvas.Clear()

        if alleStorung == "":
            zeilen = 8
        else:
            zeilen = 3

        try:
            if len(current_deps) == 0 or zeilen == 0:
                graphics.DrawText(canvas, font, 1, posVert + 10, textColor, current_deps[0]["stationName"])
                graphics.DrawLine(canvas, 0, posVert + 13, 255, posVert + 13, textColor)

                graphics.DrawText(canvas, font, 10, 20, textColor, "Bitte Aushangfahrplan beachten!")
                graphics.DrawText(canvas, font, 10, 45, textColor, "Transitous broke at this station..")
                graphics.DrawText(canvas, font, 10, 55, textColor, "Have a :3 as an apology")
            elif datetime.fromisoformat(current_deps[0]["scheduledDep"]) - datetime.now(tz=pytz.timezone("Europe/Berlin")) > timedelta(hours=2):
                graphics.DrawText(canvas, font, 1, posVert + 10, textColor, current_deps[0]["stationName"])
                if current_deps[0]["weatherTemp"] is not None:
                    weatherTemp = current_deps[0]["weatherTemp"]
                    graphics.DrawText(canvas, font, 183, posVert + 10, textColor, f"{weatherTemp}°C")

                graphics.DrawText(canvas, font, 1, posVert + 10, textColor, current_deps[0]["stationName"])
                graphics.DrawLine(canvas, 0, posVert + 13, 255, posVert + 13, textColor)
                
                graphics.DrawText(canvas, font, 215, posVert + 10, textColor, current_deps[0]["shortTime"])
                graphics.DrawLine(canvas, 0, posVert + 13, 255, posVert + 13, textColor)
                graphics.DrawText(canvas, font, 10, 30, textColor, "Keine Abfahrten in")
                graphics.DrawText(canvas, font, 10, 45, textColor, "den nächsten 2 Stunden.")

            else:

                

                for num in range(min(zeilen, len(current_deps))):
                    #depWidth = len(current_deps[num]["departure"]) * 7
                    
                    ## Header
                    graphics.DrawText(canvas, font, 1, posVert + 10, textColor, current_deps[num]["stationName"])

                    if current_deps[num]["weatherTemp"] is not None:
                        #print(f"Weather: {current_deps[num]['weatherTemp']}°C")
                        weatherTemp = current_deps[num]["weatherTemp"]
                        graphics.DrawText(canvas, font, 183, posVert + 10, textColor, f"{weatherTemp}°C")
                    #else:
                    #print("No weather data")

                    graphics.DrawText(canvas, font, 215, posVert + 10, textColor, current_deps[num]["shortTime"])
                    graphics.DrawLine(canvas, 0, posVert + 13, 255, posVert + 13, textColor)

                    
                    #Line Background Color Block
                    # Draw an 8x7 block at (x, y) with color (r, g, b)
                    x, y = 0 , posVert + 16 + num * 13  # top-left corner
                
                    routeColor = current_deps[num]["routeColor"]
                    routeColorHex = hex_to_rgb(routeColor)

                    routeTextColor = current_deps[num]["routeTextColor"]
                    routeTextColorHex = hex_to_rgb(routeTextColor)
                    routeTextColorHex = graphics.Color(routeTextColorHex[0], routeTextColorHex[1], routeTextColorHex[2])

                    if len(current_deps[num]["line"]) > 3:
                        lineColorBGlength = 5 + len(current_deps[num]["line"]) * 5
                    else:
                        lineColorBGlength = 19

                    for dx in range(lineColorBGlength):
                        for dy in range(9):
                            canvas.SetPixel(x + dx, y + dy, routeColorHex[0], routeColorHex[1], routeColorHex[2])


                    #Calculating delay
                    scheduledDep = current_deps[num]["scheduledDep"]
                    actualDep = current_deps[num]["depTimestamp"]

                    scheduled_dt = datetime.fromisoformat(scheduledDep)
                    actual_dt = datetime.fromisoformat(actualDep)
                    
                    depDelay = int((actual_dt - scheduled_dt).total_seconds() / 60)

                    if depDelay >= 1 and depDelay <= 3:
                        graphics.DrawText(canvas, font, 201, posVert + 24 + num * 13, graphics.Color(255, 64, 0), f"+{depDelay}")
                    if depDelay >= 4 and depDelay <= 9:
                        graphics.DrawText(canvas, font, 201, posVert + 24 + num * 13, graphics.Color(255, 0, 0), f"+{depDelay}")
                    if depDelay >= 10 and depDelay <= 180:
                        graphics.DrawText(canvas, font, 195, posVert + 24 + num * 13, graphics.Color(255, 0, 0), f"+{depDelay}")
                    if depDelay <= -1:
                        graphics.DrawText(canvas, font, 201, posVert + 24 + num * 13, graphics.Color(182, 255, 140), f"{depDelay}")
                

                    #Line
                    graphics.DrawText(canvas, font, 1, posVert + 24 + num * 13, routeTextColorHex, current_deps[num]["line"])
                    #Departure TIme

                    #Destination logic
                    if len(current_deps[num]["line"]) > 3:
                        destXPos = 12 + len(current_deps[num]["line"]) * 5
                    else:
                        destXPos = 22

                    if not (current_deps[num]["cancelled"] in ("Ausfall") and cycle_count % 2 ==0):
                        destinationText = current_deps[num]["destination"]
                        destinationLength = len(destinationText)
                        if destinationLength > 36 and depDelay == 0:
                            destinationText = destinationText[:36]
                        elif destinationLength > 33 and depDelay != 0:
                            destinationText = destinationText[:33]
                        graphics.DrawText(canvas, font, destXPos, posVert + 24 + num * 13, textColor, destinationText)
                    else: #Flashing
                        graphics.DrawText(canvas, font, destXPos, posVert + 24 + num * 13, textColor, "entfällt")
                        graphics.DrawText(canvas, font, destXPos, posVert + 24 + num * 13, textColor, "")
                    
                    if any([x == time for x in [(current_deps[num]["liveDep"]) , (current_deps[num]["unliveDep"])] for time in ("sofort","in 1 min")]) and cycle_count % 2 == 0:
                        graphics.DrawText(canvas, font, 215, posVert + 25 + num * 13, textColor, "¥")
                    else: #What to do if no real time data
                        if (current_deps[num]["liveDep"]) != "":
                            graphics.DrawText(canvas, font, 215, posVert + 24 + num * 13, textColor, current_deps[num]["liveDep"])
                        else:          
                            graphics.DrawText(canvas, font, 215, posVert + 24 + num * 13, textColor, current_deps[num]["unliveDep"])
                            graphics.DrawText(canvas, font, 247, posVert + 24 + num * 13, graphics.Color(255, 0, 0), "©")
                
                
            
                # --- SCROLLING LOGIC START ---
                total_lines = zeilen
                visible_lines = 4
                line_height = 13

                max_scroll = -line_height * (total_lines - visible_lines)
                lines_scrolled = abs(posVert) // line_height

                if not scrolling_up and not end_pause:
                    # Downward scrolling with pause every 4 lines
                    if not is_paused and lines_scrolled % 4 == 0 and lines_scrolled != 0 and last_pause_pos != lines_scrolled:
                        is_paused = True
                        pause_start_time = time.time()
                        last_pause_pos = lines_scrolled

                    if is_paused:
                        if time.time() - pause_start_time >= pause_duration:
                            is_paused = False
                    else:
                        posVert -= 1

                    # If reached the end, start end pause
                    if posVert <= max_scroll:
                        posVert = max_scroll
                        end_pause = True
                        end_pause_start = time.time()
                elif end_pause:
                    # Wait at the end for 5 seconds
                    if time.time() - end_pause_start >= pause_duration:
                        end_pause = False
                        scrolling_up = True
                elif scrolling_up:
                    # Scroll up without pausing
                    posVert += 1
                    if posVert >= 0:
                        posVert = 0
                        scrolling_up = False
                        is_paused = True
                        pause_start_time = time.time()
                        last_pause_pos = None
                # --- SCROLLING LOGIC END ---

        except Exception as e:
            print(f"verkackt {e}")

        update_counter = update_counter + 1
        if update_counter >= updateInterval:
            update_counter = 0
            cycle_count = cycle_count + 1
            if cycle_count >= 14:
                cycle_count = 0

                web_value = stop_point_value.value
                stopPoints = []
                for station in web_value.splitlines():
                    stopPoints.append(station)
                    
                stop_index_counter = stop_index_counter + 1
                if stop_index_counter >= len(stopPoints):
                    stop_index_counter = 0

                Thread(target=get_departures, args=[stopPoints[stop_index_counter]]).start()

        if not alleStorung == "":
            lenScroll = graphics.DrawText(canvas, font, pos, 61, textColor, alleStorung)
            lenScroll = graphics.DrawText(canvas, font, pos + lenScroll, 61, textColor, alleStorung)
            pos -= 1
            if (pos <= -lenScroll):
                pos = 0

        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(1/updateInterval)


    elif displayDesign == "kvb":
        canvas.Clear()
        zeilen = 5
        try:
            # Header (drawn once)
            for dx in range(256):
                    for dy in range(13):
                        canvas.SetPixel(0 + dx, 0 + dy, 0, 0, 128)
            dep = current_deps[0]
            graphics.DrawText(canvas, font, 1, posVert + 10, textColor, dep["shortDate"])
            graphics.DrawText(canvas, font, 65, posVert + 10, textColor, dep["shortTime"])
            graphics.DrawText(canvas, font, 170, posVert + 10, textColor, "Gleis")
            graphics.DrawText(canvas, font, 238, posVert + 10, textColor, "in")
            
            for num in range(min(zeilen, len(current_deps))):
                dep = current_deps[num]

                #Background Color Block
                x, y = 0 , posVert + 13 + num * 13  # top-left corner
                blue2 = graphics.Color(0, 0, 128)
                blue1 = graphics.Color(0, 0, 192)
                for dx in range(256):
                    for dy in range(13):
                        if num % 2 == 0:
                            canvas.SetPixel(x + dx, y + dy, blue1.red, blue1.green, blue1.blue)
                        else:
                            canvas.SetPixel(x + dx, y + dy, blue2.red, blue2.green, blue2.blue)

                #Individual Departures
                graphics.DrawText(canvas, font, 1, posVert + 23 + num * 13, textColor, dep["line"])
                graphics.DrawText(canvas, font, 30, posVert + 23 + num * 13, textColor, dep["destination"])
                graphics.DrawText(canvas, font, 182, posVert + 23 + num * 13, textColor, dep["track"])
                if dep["liveDep"] != "":
                    graphics.DrawText(canvas, font, 215, posVert + 23 + num * 13, textColor, dep["liveDep"])
                else:
                    graphics.DrawText(canvas, font, 215, posVert + 23 + num * 13, textColor, dep["unliveDep"])



        except Exception as e:
            print(f"verkackt beim rendern {e}")

        update_counter = update_counter + 1
        if update_counter >= updateInterval:
            update_counter = 0
            cycle_count = cycle_count + 1
            if cycle_count >= 14:
                cycle_count = 0

                web_value = stop_point_value.value
                stopPoints = []
                for station in web_value.splitlines():
                    stopPoints.append(station)
                    
                stop_index_counter = stop_index_counter + 1
                if stop_index_counter >= len(stopPoints):
                    stop_index_counter = 0

                Thread(target=get_departures, args=[stopPoints[stop_index_counter]]).start()
        
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(1/updateInterval)