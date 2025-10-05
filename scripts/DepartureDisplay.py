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

url = "https://api.transitous.org/api/v5/stoptimes?stopId="
headers = {'Content-Type': 'application/xml'}

stopPoints = ["de-DELFI_de%3A08212%3A3%3A3%3A3","de-DELFI_de:08212:1001:1:1"]
track = ""
#stopPoint = f"de:08212:3{track}"

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
font.LoadFont("fonts/kvv-custom-14.bdf")
textColor = graphics.Color(255, 120, 0)

alleStorung = ""

current_deps = []

def get_departures(stopPoint):
    currentTime = (datetime.now()+timedelta(hours=0)).astimezone(tz=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    currentTimestamp = datetime.now().astimezone(tz=pytz.utc).timestamp()
    r = requests.get(url=url + stopPoint + "&n=20", headers=headers)
    r.encoding = "utf-8"
    newr = json.loads(r.text)

    shortTime = datetime.now().strftime("%H:%M")

    deps = []

    #print(newr)
    stationName = newr["place"]["name"]

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

        TOC = stopeventresult["agencyName"]
        scheduledDep = place["scheduledDeparture"]

        print(PrintLive, PrintUnlive, LineNumber, ShortDest, Cancelled, BestDeparture)
        
        deps.append({"shortTime": shortTime, "stationName": stationName, "liveDep": liveDep, "unliveDep": unliveDep, "depTimestamp": BestDeparture, "scheduledDep":scheduledDep, "TOC":TOC, "line": LineNumber, "destination": ShortDest,
                     "cancelled": Cancelled})

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

lineColorBG = {
    "1":(236, 27, 36),
    "2":(0, 113, 187),
    "3":(147, 113, 57),
    "4":(212, 168, 0),
    "5":(0, 191, 242),
    "8":(246, 148, 31),
    "17":(100, 1, 2),
    "18":(18, 114, 73),
    "NL1":(236, 27, 36),
    "NL2":(0, 113, 187),
    "S1":(0, 166, 110),
    "S11":(0, 166, 110),
    "S12":(0, 166, 110),
    "S2":(158, 103, 171),
    "S3":(212, 168, 0),
    "S31":(0, 169, 157),
    "S32":(0, 169, 157),
    "S4":(158, 25, 77),
    "S41":(190, 214, 48),
    "S42":(0, 151, 186),
    "S5":(244, 152, 151),
    "S51":(244, 152, 151),
    "S52":(244, 152, 151),
    "S6":(45, 22, 71),
    "S7":(161, 152, 0),
    "S71":(161, 152, 0),
    "S8":(109, 105, 43),
    "S81":(109, 105, 43),
    "S9":(165, 206, 67),

    "FEX":(0, 166, 110),

    "E":(171, 171, 171),
}





while True:
    canvas.Clear()

    if alleStorung == "":
        zeilen = 8
    else:
        zeilen = 3

    try:
        if len(current_deps) == 0 or zeilen == 0:
            graphics.DrawText(canvas, font, 10, 20, textColor, "Bitte Aushangfahrplan beachten!")
            graphics.DrawText(canvas, font, 10, 45, textColor, "Transitous broke at this station..")
            graphics.DrawText(canvas, font, 10, 55, textColor, "Have a :3 as an apology")
        else:

            

            for num in range(min(zeilen, len(current_deps))):
                #depWidth = len(current_deps[num]["departure"]) * 7
                
                ## Header
                graphics.DrawText(canvas, font, 1, posVert + 10, textColor, current_deps[num]["stationName"])
                graphics.DrawText(canvas, font, 215, posVert + 10, textColor, current_deps[num]["shortTime"])
                graphics.DrawLine(canvas, 0, posVert + 13, 255, posVert + 13, textColor)

                
                #Line Background Color Block
                # Draw an 8x7 block at (x, y) with color (r, g, b)
                x, y = 0 , posVert + 16 + num * 13  # top-left corner

                line = current_deps[num]["line"]
                toc = current_deps[num]["TOC"]

                if any(x in toc for x in ["Albtal-Verkehrs-Gesellschaft", "Tram VBK","DB Regio AG Mitte Region Südwest"]):
                    if line in lineColorBG:
                        lcbr, lcbg, lcbb = lineColorBG[line]
                        lineColorText = graphics.Color(255, 255, 255)
                    else:
                        lcbr, lcbg, lcbb = (0, 0, 0)
                        lineColorText = textColor
                else:
                    if any(x in toc for x in ["Bus VBK"]):
                        lcbr, lcbg, lcbb = (144, 38, 143)
                        lineColorText = graphics.Color(255, 255, 255)
                    else:
                        lcbr, lcbg, lcbb = (0, 0, 0)
                        lineColorText = textColor
                

                for dx in range(19):
                    for dy in range(9):
                        canvas.SetPixel(x + dx, y + dy, lcbr, lcbg, lcbb)


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
                graphics.DrawText(canvas, font, 1, posVert + 24 + num * 13, lineColorText, current_deps[num]["line"])
                #Departure TIme

                #Destination logic
                if len(current_deps[num]["line"]) > 3:
                    destXPos = 12 + len(current_deps[num]["line"]) * 5
                else:
                    destXPos = 22

                if not (current_deps[num]["cancelled"] in ("Ausfall") and cycle_count % 2 ==0):
                    graphics.DrawText(canvas, font, destXPos, posVert + 24 + num * 13, textColor, current_deps[num]["destination"])
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