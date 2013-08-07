from lxml import etree
from pykml.factory import KML_ElementMaker as KML
import pbclient
from optparse import OptionParser


def createKMLFromContainer(data, filename):
    iconColors = ["ff0000ff", "ff00ff00", "ffff0000", "ff00ffff", "ffff00ff", "ffffff00"]
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
    doc.append(KML.Folder("all"))
    colorIndex = 0
    for tIndex, task in enumerate(data):
        print task
        for hIndex, house in enumerate(task.info["houses"]):
            pm = KML.Placemark(
                KML.styleUrl("#report-style-" + str(colorIndex % len(iconColors))),
                KML.name(str(tIndex) + "-" + str(hIndex)),
                KML.Point(
                    KML.coordinates("{0},{1}".format(house["geometry"]["coordinates"][0],
                                                     house["geometry"]["coordinates"][1]))
                )
            )

            doc.Folder.append(pm)
        colorIndex += 1
    out = open(filename, "wb")
    out.write(etree.tostring(doc, pretty_print=True))
    out.close()

parser = OptionParser()
parser.add_option("-k", "--api-key", dest="api_key",
                      help="PyBossa User API-KEY to interact with PyBossa",
                      metavar="API-KEY")
(options, args) = parser.parse_args()
if not options.api_key:
    parser.error("You must supply an API-KEY to create " +
                     "an application and tasks in PyBossa")
pbclient.set('api_key', options.api_key)
pbclient.set('endpoint', 'http://crowdcrafting.org')
response = pbclient.find_app(short_name='RuralGeolocator')
# Check errors:
if type(response) == dict and (response.get('status') == 'failed'):
    print "Error"
    print response
    exit(0)
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

#for now just use the json export, save as exportTest in local dir
#json_data = open('exportTest.json')
#data = json.load(json_data)
#json_data.close()
createKMLFromContainer(data, "houses.kml")
