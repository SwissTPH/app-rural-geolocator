import argparse
import math
import simplekml
import pbclient


def map_all_houses(data, filename):
    shared_style = simplekml.Style()
    shared_style.iconstyle.color = "ff0000ff"
    shared_style.labelstyle.scale = 0.5
    shared_style.iconstyle.scale = 0.5

    kml = simplekml.Kml()
    for task_index, task in enumerate(data):
        for house in task.info["houses"]:
            pnt = kml.newpoint(name=str(task_index))
            pnt.coords = [(house["geometry"]["coordinates"][0], house["geometry"]["coordinates"][1])]
            pnt.style = shared_style
    kml.save(filename)


def map_points(data, filename):
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


def calculate_distance(p1, p2):
    r = 6371
    dlat = math.radians(p2[0] - p1[0])
    dlon = math.radians(p2[1] - p1[1])
    a = (math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(p1[0])) * math.cos(math.radians(p2[0])) *
         math.sin(dlon/2) * math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = r * c
    return d * 1000


def filter_points(tasks, distance):
    filtered_points = []
    for task in tasks:
        for house in task.info['houses']:
            merged = False
            coordinates = house['geometry']['coordinates']
            for point in filtered_points:
                if calculate_distance(point[0], coordinates) < distance:
                    point[0] = [(point[0][0] + coordinates[0]) / 2, (point[0][1] + coordinates[1]) / 2]
                    point[1] += 1
                    merged = True
                    break
            if not merged:
                filtered_points.append([coordinates, 1])
    return filtered_points


def get_results(app):
    more_results = len(pbclient.get_taskruns(app_id=app.id, limit=1, offset=0)) > 0
    limit = 300
    offset = 0
    task_runs = []
    while more_results:
        response = pbclient.get_taskruns(app_id=app.id, limit=limit, offset=offset)
        if len(response) > 0:
            task_runs += response
            offset += limit
        else:
            more_results = False
    return task_runs


def process_results(task_runs):
    batches = {}
    for task in task_runs:
        if 'batch' in task.info.keys():
            batch = task.info['batch']
        else:
            batch = 'na'
        if not batch in batches.keys():
            batches[batch] = []
        batches[batch].append(task)
    for batch in batches.keys():
        map_all_houses(batches[batch], batch + "_allpoints.kml")
        houses = filter_points(batches[batch], int(args.radius))
        print("Batch: " + batch + " Houses: " + str(len(houses)))
        map_points(houses, batch + "_houses.kml")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--api-key", help="PyBossa User API-KEY to interact with PyBossa", required=True)
    parser.add_argument("-s", "--server", help="PyBossa URL http://domain.com/", required=True)
    parser.add_argument("-r", "--radius", help="Radius around points thought to be the same house", required=True)
    args = parser.parse_args()
    pbclient.set('api_key', args.api_key)
    pbclient.set('endpoint', args.server)

    response = pbclient.find_app(short_name='RuralGeolocator')
    # Get the app
    app = response[0]
    task_runs = get_results(app)
    print(len(task_runs))
    process_results(task_runs)
