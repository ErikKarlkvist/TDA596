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
from threading import Thread

from bottle import Bottle, run, request, template, HTTPResponse
from threading import Thread
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {}

    lc = 0

    log = [] # my personal log
    allLog = [] #includes personal log and incoming

    otherLogs = {}

    syncing = False

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

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[str(entry_sequence)] = modified_element
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call=False):
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
                res = requests.post(
                    'http://{}{}'.format(vessel_ip, path), data=payload)
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

    def propagate_to_vessels(path, payload=None, req='POST'):

        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)

                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(
                        vessel_id)

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
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sortBoard(board))
    # ------------------------------------------------------------------------------------------------------

    @app.post('/board')
    def client_add_received():

        global board, lc, node_id, log, allLog
        try:
            lc = 1 + int(lc)

            new_entry = request.forms.get('entry')

            body = {
                'entry': new_entry,
                'node': node_id,
                'localClock': lc,
                'action': "add"
            }

            log.append(body)
            allLog.append(body)
            # generate_id()
            # you might want to change None here
            add_new_element_to_store(lc, new_entry)
            thread = Thread(target=propagate_to_vessels, args=(
                "/propagate/add/"+str(lc), json.dumps(body), 'POST'))
            thread.deamon = True
            thread.start()
            # Returning true gives a weird error so we return a describing string instead
            return "Latest entry: " + new_entry

        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):

        global board, node_id, log, allLog
        print("ATION RECEVED")

        action = ""  # action that determines modify or delete to be sent to propagate_to_vessels()

        # used 'forms' to get the values of entry and delete
        entryStr = request.forms.get('entry')
        deleteStr = request.forms.get('delete')
        try:
            if(deleteStr == "1"):
                action = "delete"

                body = {
                    'entry': entryStr,
                    'node': node_id,
                    'localClock': element_id,
                    'action': "delete"
                }
                log.append(body)
                allLog.append(body)
                delete_element_from_store(element_id)

            if(deleteStr == "0"):
                print("modify")
                action = "modify"
                body = {
                    'entry': entryStr,
                    'node': node_id,
                    'localClock': element_id,
                    'action': "modify",
                    "oldEntry": board[str(element_id)]
                }
                log.append(body)
                allLog.append(body)
                print(log)
                modify_element_in_store(element_id, entryStr)

            #t = Thread(target=propagate_to_vessels, args=(
           #     ('/propagate/' + action + '/' + str(element_id)), entryStr))
          #  t.deamon = True
          # t.start()

            # Returning true gives a weird error so we return a describing string instead
            return "Action successfull"
        except Exception as e:
            print("FAIL")
            print(e)
        return False

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):

        global lc, node_id, allLog

        body = json.loads(request.body.read())
        # log.append(body)

        entry = body['entry']
        rc = int(body['localClock'])

        if(action == "add"): #only add action is propagated here
            print("BEFORE: " + str(lc))
            if rc > lc:  # always take the largest clock
                lc = rc
                add_new_element_to_store(lc, entry)
            elif rc == lc:  # if equal, prioritize on node with lowest id
                if node_id > int(body['node']):
                    other_entry = board[str(lc)]
                    print("Other entry: " + other_entry)
                    modify_element_in_store(lc, entry)
                    lc = lc + 1
                    add_new_element_to_store(lc, other_entry)
                else:
                    lc = lc + 1
                    add_new_element_to_store(lc, entry)
            else:
                lc = lc + 1
                add_new_element_to_store(lc, entry)

            body['localId'] = lc
            allLog.append(body)
       
        

    @app.get("/take_snapshot/")
    def take_snapshot():
        global node_id, log, syncing
        syncing = True
        return json.dumps(log)

    @app.post("/sync_snapshot/")
    def take_snapshot():
        global board
        syncing = False
        newBoard = json.loads(request.body.read())
        board = newBoard

    def sync():
        global otherLogs, log, node_id, syncing, board, allLog
        time.sleep(20)
        if not syncing:
            syncing = True
            print("SYNCING")
            print("ALL LOG " + str(allLog))
            start_receiving_logs()
            otherLogs[str(node_id)] = log[:] ## clone my log, otherwise we edit at same refernce
            # each log contains what they have sent
            completeLog = {}
            allIsEmpty = False
            deletedIds = []
            while(not allIsEmpty):  # keep looping until all sublogs are empty
                nextElem = {}
                deletingVesselId = -1
                deletingLog = []
                allIsEmpty = True
                for vessel_id, otherLog in otherLogs.items():
                    if(len(otherLog) > 0):
                        allIsEmpty = False  # if this is every reached we must loop again
                        if shouldReplaceNextElem(nextElem, otherLog):
                            nextElem = otherLog[0]
                            deletingVesselId = vessel_id
                            deletingLog = otherLog

                # check lc of last, set nextElem lc to this
                if len(nextElem) > 0:
                    if nextElem['action'] == "add":
                        completeLog[str(nextElem['localClock'])] = nextElem
                    elif nextElem['action'] == "modify" and nextElem['localClock'] not in deletedIds:
                        completeLog[str(nextElem['localClock'])] = nextElem
                    else:
                        deletedIds.append(str(nextElem['localClock']))
                        del completeLog[str(nextElem['localClock'])]
                    del deletingLog[0]
                    otherLogs[deletingVesselId] = deletingLog


            newBoard = createBoardFromLog(completeLog)
            board = newBoard
            sendNewBoard(newBoard)
            #propagate new board
            syncing = False  # set in a propapagation somewhere instead
        sync()

    def sendNewBoard(newBoard):
        t = Thread(target=propagate_to_vessels, args=("/sync_snapshot/", json.dumps(newBoard), 'POST'))
        t.deamon = True
        t.start()

    def shouldReplaceNextElem(nextElem, otherLog):
        if len(nextElem) > 0:
            return otherLog[0]['localClock'] < nextElem['localClock'] or (otherLog[0]['localClock'] == nextElem['localClock'] and otherLog[0]['node'] < nextElem['node'])
        else: 
            return True  

    def createBoardFromLog(log):
        newBoard = {}
        for localClock, item in log.items():
            newBoard[str(localClock)] = item['entry']
        return newBoard

    def start_receiving_logs():
        global node_id, vessel_list, otherLogs
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                res = requests.get(
                    'http://{}{}'.format(vessel_ip, "/take_snapshot/"))

                if res.status_code == 200:
                    otherLogs[str(vessel_id)] = json.loads(res.content)
                #t = Thread(target = receive_log, args =('http://{}{}'.format(vessel_ip,"/take_snapshot/")))
                #t.deamon = True
                # t.start()

    # properly sort board (normal sorting doesn't fork since the values are strings)

    def sortBoard(board):
        integerParsedBoard = {int(float(k)): v for k, v in board.items()}
        return sorted(integerParsedBoard.iteritems())
    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for postGive it to the students-----------------------------------------------------------------------------------------------------
    # Execute the code

    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(
            description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid',
                            default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1,
                            type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv+1):
            t = Thread(target=sync, args=(""))
            t.deamon = True
            t.start()
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
