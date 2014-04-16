#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Citizen Cyberscience Centre, Swiss TPH
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import shapefile
import logging
from argparse import ArgumentParser
from ConfigParser import RawConfigParser
import requests
import pbclient
import time
from matplotlib.path import Path
from matplotlib.transforms import Bbox


def check_api_error(api_response):
    """Check if returned API response contains an error"""
    if type(api_response) == dict and (api_response.get('status') == 'failed'):
        print(api_response)
        raise requests.exceptions.HTTPError


def format_error(module, error):
    """Format the error for the given module"""
    logging.error(module)
    # Beautify JSON error
    if type(error) == list:
        print "Application not found"
    else:
        print json.dumps(error, sort_keys=True, indent=4, separators=(',', ': '))
    exit(1)


def polygon_file_to_path(filename):
    area_polygon = None
    if filename.endswith(".json"):
        #TODO: use proper structure
        area_outline = json.load(open(filename))
        area_outline_vertices = []
        for point in area_outline:
            area_outline_vertices.append(point)
        area_polygon = Path(area_outline_vertices)
    if filename.endswith(".shp"):
        #TODO: not yet working
        sf = shapefile.Reader(filename)
        shapes = sf.shapes()
        area_polygon = Path(sf.shape(0).points)
    return area_polygon


if __name__ == "__main__":
    # Arguments for the application
    usage = "usage: %prog [options]"
    parser = ArgumentParser(usage)
    # URL where PyBossa listens
    parser.add_argument("-s", "--server", help="PyBossa URL http://domain.com/", required=True)
    # API-KEY
    parser.add_argument("-k", "--api-key", help="PyBossa User API-KEY to interact with PyBossa", required=True)
    # Create App
    parser.add_argument("-c", "--create-app", action="store_true", help="Create the application")
    # Create tasks, using a polygon for the area
    parser.add_argument("-t", "--task-config", help="File which contains configuration for task creation.")
    # Update template for tasks and long_description for app
    parser.add_argument("-u", "--update-template", action="store_true", help="Update Tasks template")
    # Update tasks
    parser.add_argument("-q", "--update-tasks", help="Update tasks", action="store_true")
    # Verbose?
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    # Load app details
    try:
        app_json = open('app.json')
        app_config = json.load(app_json)
        app_json.close()
    except IOError as e:
        print "app.json is missing! Please create a new one"
        exit(0)

    pbclient.set('endpoint', args.server)
    pbclient.set('api_key', args.api_key)

    if args.verbose:
        print('Running against PyBosssa instance at: %s' % args.server)
        print('Using API-KEY: %s' % args.api_key)

    if args.create_app:
        try:
            response = pbclient.create_app(app_config['name'],
                                           app_config['short_name'],
                                           app_config['description'])
            check_api_error(response)
            response = pbclient.find_app(short_name=app_config['short_name'])
            check_api_error(response)
            app = response[0]
            app.long_description = open('long_description.html').read()
            app.info['task_presenter'] = open('template.html').read()
            app.info['thumbnail'] = app_config['thumbnail']
            app.info['tutorial'] = open('tutorial.html').read()
        except:
            format_error("pbclient.create_app or pbclient.find_app", response)

        try:
            response = pbclient.update_app(app)
            check_api_error(response)
        except:
            format_error("pbclient.update_app", response)

    if args.task_config:
        config = RawConfigParser()
        config.read(args.task_config)
        response = pbclient.find_app(short_name=app_config['short_name'])
        app = response[0]
        app_id = app.id
        #polygon around area to be tasked, as list of (lat, long) lists
        islandPolygon = polygon_file_to_path(config.get("area", "polygon_file"))
        extent = islandPolygon.get_extents().get_points()
        #The northern, southern, western, and eastern bounds of the area to work on.
        nb = extent[1][0]
        wb = extent[0][1]
        sb = extent[0][0]
        eb = extent[1][1]
        print (nb, wb, sb, eb)
        #Size of the tasks, into how many rows and columns should the area be divided.
        task_cols = int(config.get("tasksize", "task_cols"))
        task_rows = int(config.get("tasksize", "task_rows"))
        boundary = float(config.get("tasksize", "boundary"))
        ns_step = (sb - nb) / task_rows
        ns_boundary = ns_step * boundary
        we_step = (eb - wb) / task_rows
        we_boundary = we_step * boundary
        task_counter = 0
        res = requests.get(args.server + '/api/app')
        remaining_requests = int(res.headers['x-ratelimit-remaining'])
        for col in range(task_cols):
            wbr = wb + col * we_step
            ebr = wb + (col + 1) * we_step
            for row in range(task_rows):
                while remaining_requests < 10:
                    res = requests.get(args.server + '/api/app')
                    remaining_requests = int(res.headers['x-ratelimit-remaining'])
                    if remaining_requests < 10:
                        print(remaining_requests)
                        time.sleep(60)
                        print(remaining_requests)
                nbc = nb + row * ns_step
                sbc = nb + (row + 1) * ns_step
                if islandPolygon.intersects_bbox(Bbox([[nbc, wbr], [sbc, ebr]])):
                    task_info = dict(question=app_config['question'], n_answers=config.get("meta", "n_answers"),
                                     westbound=wbr, eastbound=ebr, northbound=nbc, southbound=sbc,
                                     westmapbound=wbr - we_boundary, eastmapbound=ebr + we_boundary,
                                     northmapbound=nbc - ns_boundary, southmapbound=sbc + ns_boundary,
                                     location=str(row) + "_" + str(col), batch=config.get("meta", "batch_name"))
                    response = pbclient.create_task(app_id, task_info)
                    check_api_error(response)
                    task_counter += 1
                    print(task_counter)
                    remaining_requests -= 1

    if args.update_template:
        print "Updating app template"
        try:
            response = pbclient.find_app(short_name=app_config['short_name'])
            check_api_error(response)
            app = response[0]
            app.long_description = open('long_description.html').read()
            app.info['task_presenter'] = open('template.html').read()
            app.info['tutorial'] = open('tutorial.html').read()
            response = pbclient.update_app(app)
            check_api_error(response)
        except:
            format_error("pbclient.find_app or pbclient.update_app", "")

    if args.update_tasks:
        print "Updating task question"
        try:
            response = pbclient.find_app(short_name=app_config['short_name'])
            check_api_error(response)
            app = response[0]
            n_tasks = 0
            offset = 0
            limit = 100
        except:
            format_error("pbclient.find_app", response)

        try:
            tasks = pbclient.get_tasks(app.id, offset=offset, limit=limit)
            check_api_error(tasks)
        except:
            format_error("pbclient.get_tasks", tasks)
        while tasks:
            for task in tasks:
                print "Updating task: %s" % task.id
                if ('n_answers' in task.info.keys()):
                    del(task.info['n_answers'])
                task.n_answers = int(args.number_answers)
                try:
                    response = pbclient.update_task(task)
                    check_api_error(response)
                    n_tasks += 1
                except:
                    format_error("pbclient.update_task", response)
            offset = (offset + limit)
            try:
                tasks = pbclient.get_tasks(app.id, offset=offset, limit=limit)
                check_api_error(tasks)
            except:
                format_error("pbclient.get_tasks", tasks)
        print "%s Tasks have been updated!" % n_tasks
