import argparse

from lxml import etree
from pykml.factory import KML_ElementMaker as KML
import pbclient


def createKMLFromContainer(data, filename):
    iconColors = ["ff0000ff", "ff00ff00", "ffff0000", "ff00ffff", "ffff00ff", "ffffff00",
                  "ff000077", "ff007700", "ff770000", "ff007777", "ff770077", "ff777700",
                  "ff7777ff", "ff77ff77", "ffff7777", "ff77ffff", "ffff77ff", "ffffff77",
                  "ff0077ff", "ff77ff00", "ffff0077"]
    doc = KML.Document()
    for i, color in enumerate(iconColors):
        doc.append(
            KML.Style(
                KML.IconStyle(
                    KML.color(color),
                ),
                id="report-style-" + str(i)
            )
        )
    colorIndex = 0
    for tIndex, task in enumerate(data):
        for hIndex, house in enumerate(task.info["houses"]):
            pm = KML.Placemark(
                KML.styleUrl("#report-style-" + str(colorIndex % len(iconColors))),
                KML.name(str(tIndex) + "-" + str(hIndex)),
                KML.Point(
                    KML.coordinates("{0},{1}".format(house["geometry"]["coordinates"][0],
                                                     house["geometry"]["coordinates"][1]))
                )
            )
            doc.append(pm)
        colorIndex += 1
    out = open(filename, "wb")
    out.write(etree.tostring(doc, pretty_print=True))
    out.close()

parser = argparse.ArgumentParser()
parser.add_argument("-k", "--api-key", help="PyBossa User API-KEY to interact with PyBossa", required=True)
parser.add_argument("-s", "--server", help="PyBossa URL http://domain.com/", required=True)
args = parser.parse_args()
pbclient.set('api_key', args.api_key)
pbclient.set('endpoint', args.server)

response = pbclient.find_app(short_name='RuralGeolocator')
# Check errors:
if type(response) == dict and (response.get('status') == 'failed'):
    print "Error"
    print response
# Get the app
app = response[0]
data = pbclient.get_taskruns(app_id=app.id, limit=1000, offset=0)
limit = 100
offset = 0
task_runs = []

while len(data) > 0:
    response = pbclient.get_taskruns(app_id=app.id, limit=limit, offset=offset)
    if type(response) != dict:
        # Add the new task runs
        task_runs += response
        data = response
        offset += 100
    else:
        # Break the while
        data = []

# Parse the task_run.info data to extract the GeoJSON
data = [task_run for task_run in task_runs]
print(len(data))
createKMLFromContainer(data, "houses.kml")
