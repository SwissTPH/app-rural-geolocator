import argparse
import math
import simplekml
import pbclient


def mapAllHouses(data, filename):
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


def mapPoints(data, filename):
    colors = ["ffff00ff", "ff00ffff", "ffffff00"]
    styles = []
    for color in colors:
        style = simplekml.Style()
        style.iconstyle.color = color
        style.labelstyle.scale = 0.5
        style.iconstyle.scale = 0.5
        styles.append(style)

    kml = simplekml.Kml()
    for point in data:
        pnt = kml.newpoint(name=str(point[1]))
        pnt.coords = [(point[0])]
        pnt.style = styles[min(point[1]-1, 2)]
    kml.save(filename)


def calculateDistance(p1, p2):
    r = 6371
    dlat = math.radians(p2[0] - p1[0])
    dlon = math.radians(p2[1] - p1[1])
    a = (math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(p1[0])) * math.cos(math.radians(p2[0])) *
         math.sin(dlon/2) * math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = r * c
    return d * 1000


def filterPoints(tasks, distance):
    filteredPoints = []
    for task in tasks:
        #print(task.id)
        #print(task.task_id)
        for house in task.info['houses']:
            merged = False
            coords = house['geometry']['coordinates']
            for point in filteredPoints:
                if calculateDistance(point[0], coords) < distance:
                    point[0] = [(point[0][0] + coords[0]) / 2, (point[0][1] + coords[1]) / 2]
                    point[1] += 1
                    merged = True
                    break
            if not merged:
                filteredPoints.append([coords, 1])
    return filteredPoints


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
moreResults = len(pbclient.get_taskruns(app_id=app.id, limit=1, offset=0)) > 0
limit = 300
offset = 0
task_runs = []
while moreResults:
    response = pbclient.get_taskruns(app_id=app.id, limit=limit, offset=offset)
    if len(response) > 0:
        task_runs += response
        offset += limit
    else:
        moreResults = False

print(len(task_runs))
mapAllHouses(task_runs, "allpoints.kml")
houses = filterPoints(task_runs, 5)
print(len(houses))
mapPoints(houses, "houses.kml")