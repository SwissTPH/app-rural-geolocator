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
import logging
from argparse import ArgumentParser
from requests import exceptions
import pbclient
from matplotlib.path import Path
from matplotlib.transforms import Bbox


def check_api_error(api_response):
    """Check if returned API response contains an error"""
    if type(api_response) == dict and (api_response.get('status') == 'failed'):
        raise exceptions.HTTPError


def format_error(module, error):
    """Format the error for the given module"""
    logging.error(module)
    # Beautify JSON error
    if type(error) == list:
        print "Application not found"
    else:
        print json.dumps(error, sort_keys=True, indent=4, separators=(',', ': '))
    exit(1)


if __name__ == "__main__":
    # Arguments for the application
    usage = "usage: %prog [options]"
    parser = ArgumentParser(usage)
    # URL where PyBossa listens
    parser.add_argument("-s", "--server", help="PyBossa URL http://domain.com/", default="http://crowdcrafting.org")
    # API-KEY
    parser.add_argument("-k", "--api-key", help="PyBossa User API-KEY to interact with PyBossa", required=True)
    # Create App
    parser.add_argument("-a", "--create-app", action="store_true", help="Create the application")
    # Update template for tasks and long_description for app
    parser.add_argument("-u", "--update-template", action="store_true", help="Update Tasks template")
    # Update template for tasks and long_description for app
    parser.add_argument("-c", "--create-tasks", action="store_true", help="Create tasks")
    parser.add_argument("-b", "--batch", help="Batch name", default="none")
    # Update tasks question
    parser.add_argument("-q", "--update-tasks", help="Update Tasks n_answers", action="store_true")
    # Modify the number of TaskRuns per Task
    parser.add_argument("-n", "--number-answers", help="Number of answers per task", default=1)
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

    if args.create_tasks:
        response = pbclient.find_app(short_name='RuralGeolocator')
        app = response[0]
        app_id = app.id
        #polygon around area to be tasked, as list of (lat, long) lists
        rusingaOutlineData = json.load(open('data/area.json'))
        rusingaOutlineVertices = []
        for point in rusingaOutlineData:
            rusingaOutlineVertices.append(point)
        islandPolygon = Path(rusingaOutlineVertices)
        points = islandPolygon.get_extents().get_points()
        #The northern, southern, western, and eastern bounds of the area to work on.
        nb = points[1][0]
        wb = points[0][1]
        sb = points[0][0]
        eb = points[1][1]
        print (nb, wb, sb, eb)
        #Size of the tasks, into how many rows and columns should the area be divided.
        task_cols = 40
        task_rows = 30
        ns_step = (sb - nb) / task_cols
        we_step = (eb - wb) / task_rows
        task_counter = 0
        for row in range(task_rows):
            wbr = wb + row * we_step
            ebr = wb + (row + 1) * we_step
            for col in range(task_cols):
                nbc = nb + col * ns_step
                sbc = nb + (col + 1) * ns_step
                if islandPolygon.intersects_bbox(Bbox([[nbc, wbr], [sbc, ebr]])):
                    boundary = 0.01
                    task_info = dict(question=app_config['question'], n_answers=int(args.number_answers),
                                     westbound=wbr, eastbound=ebr, northbound=nbc, southbound=sbc,
                                     westmapbound=wbr - boundary, eastmapbound=ebr + boundary,
                                     northmapbound=nbc + boundary, southmapbound=sbc - boundary,
                                     location=str(row) + "_" + str(col), batch=args.batch)
                    response = pbclient.create_task(app_id, task_info)
                    check_api_error(response)
                    task_counter += 1
                    print(task_counter)

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
