This project uses the Transitous API to display upcoming public transport departures on HUB75 RGB-LED Matrixes with the rpi-rgb-led-matrix library for Raspi.
Currently I only recommend using this if you know what you're doing, or else you'll be super confused.


Features:
- Real-Time information about many transit systems around the world
- KVV lines have corresponding line colours
- You can add multiple stations via a local webserver
- Delay and cancelation information and a symbol if there's no live data
- Style is inspired by the VBK dot matrix screens (including custom font)

How to use:
- Follow instructions for the rpi-rgb-led-matrix library's python bindings
- Clone this repo
- Install all required python modules
- If you now run the DepartureDisplay.py script, you should be able to see some departures and an IP in the console, with which you can open the web control panel.

To-Do:
- Use the line colour database by Träwelling for Germany-wide line colours
- optional weather information
- optional track information
- more costumizability (eg text colour, which modes of transport, how many pages)
- adding multiple stations to one page
- functioning brightness night mode
- fix disruption/info text row
- Web UI (like, a real one)
- "Dont use in production" webserver fix lol
- long-term: version for browser so no extra display is needed
- long-term: other library that support text boxes (and borders)

Made with ❤️ in the fox cave. Thanks to all my friends giving me support.