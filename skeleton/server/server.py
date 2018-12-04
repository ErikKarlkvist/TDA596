# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: John Doe
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
import random
import time
from threading import Thread

from bottle import Bottle, run, request, template, HTTPResponse
from threading import Thread
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()
    board = {}

    #FOR LAB3
    lc = 0
    log = []
    monitor = -1
    snapshot = False

    #FOR MONITOR
    countVessels = 0
    finallog = []



    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Should nopt be given to the student
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(entry_sequence, element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[str(entry_sequence)] = element
            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            board[str(entry_sequence)] = modified_element
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            del board[str(entry_sequence)]
            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # should be given to the students?
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        try:
            if 'POST' in req:
                res = requests.post('http://{}{}'.format(vessel_ip, path), data=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
        return success

    def propagate_to_vessels(path, payload = None, req = 'POST'):

        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)

                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)



    def sendSnapshot():
        global monitor, lc, node_id
        if(str(node_id) == str(monitor)):

            body = {
                'entry': 'null',
                'node': node_id,
                'localClock': lc,
                'snapshot': True,
            }

            snapshot = True

            log.append(body)
            thread = Thread(target = propagate_to_vessels, args = ("/propagate/add/"+str(lc), json.dumps(body), 'POST'))
            thread.deamon = True
            thread.start()

    def sortFinalLog(logs):
        print("sorting finallog")

        body = body = {
                'entry': 'null',
                'node': node_id,
                'localClock': lc,
                'snapshot': False,
            }

        t = Thread(target = propagate_to_vessels,args =(('/propagate/snapshot/' + str(monitor)), None))
        t.deamon = True
        t.start()
    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sortBoard(board), members_name_string='knoph@student.chalmers.se & erikarlk@student.chalmers.se') 

    @app.get('/board')
    def get_board():
        global board, node_id
        print board
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sortBoard(board))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        
        global board, lc, node_id
        try:
            lc = 1 + int(lc)

            new_entry = request.forms.get('entry')

            body = {
                'entry': new_entry,
                'node': node_id,
                'localClock': lc,
                'snapshot': False,
            }

            log.append(body)
            add_new_element_to_store(lc, new_entry) 
            thread = Thread(target = propagate_to_vessels, args = ("/propagate/add/"+str(lc), json.dumps(body), 'POST')) #säger till de andra vesselsen vad min logg ligger på
            thread.deamon = True
            thread.start()
            return "Latest entry: " + new_entry #Returning true gives a weird error so we return a describing string instead

        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):

        global board, node_id, log

        action = "" #action that determines modify or delete to be sent to propagate_to_vessels()

        entryStr = request.forms.get('entry') #used 'forms' to get the values of entry and delete
        deleteStr = request.forms.get('delete')

        try:
            if(deleteStr == "1"): 
                action = "delete" 
                delete_element_from_store(element_id)

            if(deleteStr == "0"):
                action = "modify"
                modify_element_in_store(element_id, entryStr)

            t = Thread(target = propagate_to_vessels,args =(('/propagate/'+ action +'/' + str(element_id)), entryStr))
            t.deamon = True
            t.start()

            return "Action successfull" #Returning true gives a weird error so we return a describing string instead
        except Exception as e:
            print e
        return False
        
    @app.post('/propagate/monitor')
    def monitorLogs():
        global countVessels, finalLog

        if(countVessels < len(vessel_list)+1): #if you haven't received all vessels logs yet
            vesselLog = json.loads(request.body.read())
            finallog.append(vesselLog)
            countVessels = countVessels+1
        else:
            sortFinalLog(finallog) # when you've received them all, sort them

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id): #när jag får från nån annan vessel

        global lc, node_id

        body = json.loads(request.body.read())
        log.append(body)

        if(body['snapshot'] == True):
            snapshot = True
            t = Thread(target = contact_vessel(str(monitor),"/propagate/monitor", json.dumps(log), 'POST'))#skicka din logg till monitorn
            t.deamon = True
            t.start()
            while(snapshot == True):
                time.sleep(1)


        entry = body['entry']
        rc = int(body['localClock'])

        if(action == "delete"):
            delete_element_from_store(element_id)

        if(action == "modify"):
            modify_element_in_store(element_id, entry)

        if(action == "add"):
            print("BEFORE: " + str(lc))
                lc = lc + 1
                add_new_element_to_store(lc, entry)

            print("AFTER: "+str(lc))
    
        
    #properly sort board (normal sorting doesn't work since the values are strings)
    def sortBoard(board): 
        integerParsedBoard = {int(float(k)): v for k, v in board.items()}
        return sorted(integerParsedBoard.iteritems())


    def initiateProgram():
        global monitor
        time.sleep(5)
        #monitor = random.randint(1,len(vessel_list)+1)
        monitor = 2

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for postGive it to the students-----------------------------------------------------------------------------------------------------
    # Execute the code
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        #initiateProgram()
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
        time.sleep(60.)