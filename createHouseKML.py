import argparse

import simplekml
import pbclient


def createKMLFromContainer(data, filename):
    sharedStyle = simplekml.Style()
    sharedStyle.iconstyle.color = "ff0000ff"
    sharedStyle.labelstyle.scale = 0.5
    sharedStyle.iconstyle.scale = 0.5

    kml = simplekml.Kml()
    for tIndex, task in enumerate(data):
        for house in task.info["houses"]:
            pnt = kml.newpoint(name=str(tIndex))
            pnt.coords = [(house["geometry"]["coordinates"][0], house["geometry"]["coordinates"][1])]
            pnt.style = sharedStyle
    kml.save(filename)


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
