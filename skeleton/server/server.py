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
    leader = 0

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
            print(e)
        return success

    def modify_element_in_store(entry_sequence, modified_element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board[str(entry_sequence)] = modified_element
            success = True
        except Exception as e:
            print(e)
        return success

    def delete_element_from_store(entry_sequence, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            del board[str(entry_sequence)]
            success = True
        except Exception as e:
            print(e)
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
                print('Non implemented feature!')
            # result is in res.text or res.json()
            print(res)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print(e)
        return success

    def propagate_to_vessels(path, payload=None, req='POST'):

        global vessel_list, node_id

        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id:  # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)

                if not success:
                    print("\n\nCould not contact vessel {}\n\n".format(vessel_id))

    def propagate_to_next_vessel(path, payload=None, req='POST'):

        global vessel_list, node_id

        ip = '10.1.0.1'

        if node_id < len(vessel_list):
            ip = '10.1.0.'+str(node_id+1)

        thread = Thread(target = contact_vessel, args = (ip, path, payload, req))
        thread.deameon = True
        thread.start()

    # --------------------------------------------------------------------------
    def handle_leader(lista):
        global leader
        highest = 0
        for vessel_id in lista:
            if vessel_id > highest:
                highest = vessel_id
        leader = highest
        print("FOUND LEADER: " + str(leader))
        thread = Thread(target = propagate_to_vessels, args =('/election/leader/' + str(leader), None , 'POST'))
        thread.deamon = True
        thread.start()
        #propagate_to_vessels('/election/leader/' + str(leader) , payload=None , req='POST')

    def handle_election(lista):
        global node_id

        if node_id in lista:
            print("FOUND MYSELF: " + str(node_id))
            handle_leader(lista)
            
        else:
            print("Innan: " + str(lista))
            lista.append(node_id)
            print("Efter: " + str(lista))

            propagate_to_next_vessel('/election/circulate/', json.dumps(lista), req='POST')

    def leader_handle_element(action, entry):
        global board

        entry_id = -1
        if(action == "add"): 
            entry_id = len(board) + 1
            add_new_element_to_store(entry_id, entry)
        
        thread = Thread(target = propagate_to_vessels, args = ('/propagate/' + action + "/" + str(entry_id), entry, 'POST'))
        thread.deamon = True
        thread.start()

    # -----------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()), members_name_string='knoph@student.chalmers.se & erikarlk@student.chalmers.se')

    @app.get('/board')
    def get_board():
        global board, node_id
        print(board)
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------

    @app.post('/board')
    def client_add_received():

        global board, node_id
        try:
            new_entry = request.forms.get('entry')
            #element_id = int(round(time.time()*1000000))
            # generate_id()
            #add_new_element_to_store(element_id, new_entry)
            if(node_id != leader):
                thread = Thread(target=contact_vessel, args=('10.1.0.'+ str(leader), "/leader/add/", new_entry, 'POST'))
                thread.deamon = True
                thread.start()
            else:
                leader_handle_element("add", new_entry)

            return "Latest entry: " + new_entry # Returning true gives a weird error so we return a describing string instead

        except Exception as e:
            print(e)
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):

        global board, node_id

        action = ""  # action that determines modify or delete to be sent to propagate_to_vessels()

        # used 'forms' to get the values of entry and delete
        entryStr = request.forms.get('entry')
        deleteStr = request.forms.get('delete')

        try:
            if(deleteStr == "1"):
                action = "delete"
                delete_element_from_store(element_id)

            if(deleteStr == "0"):
                action = "modify"
                modify_element_in_store(element_id, entryStr)

            t = Thread(target=propagate_to_vessels, args=(
                ('/propagate/' + action + '/' + str(element_id)), entryStr))
            t.deamon = True
            t.start()

            # Returning true gives a weird error so we return a describing string instead
            return "Action successfull"
        except Exception as e:
            print(e)
        return False

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):

        entry = request.body.read()

        if(action == "delete"):
            delete_element_from_store(element_id)

        if(action == "modify"):
            modify_element_in_store(element_id, entry)

        if(action == "add"):
            add_new_element_to_store(element_id, entry)

    @app.post('/election/circulate/')
    def election_received():
        body = request.body.read()
        prev_list = json.loads(body)
        handle_election(prev_list)

    @app.post('/election/leader/<leader_id>')
    def leader_found(leader_id):
        global leader
        leader = leader_id
        print("LEADER ELECTED: " + leader)

    @app.post('/leader/<action>')
    def leader_propagation_recieved(action):
        entry = request.body.read()
        leader_handle_element(action, entry)



    def generate_id():
        global board
        id = 0
        # A start that is higher than the amount of vessels to avoid collisions
        rs = (len(vessel_list)+1)
        re = 10000001  # random end
        if(len(board) == 0):  # if board has length 0, just set random number
            id = random.randint(rs, re)
        else:
            # access first key in board just to have a key that already exist in while loop
            id = board.keys()[0]
            while(id in board):  # if id is in board, retry until it's not
                id = random.randint(rs, re)
        return id

    def initiate_election():
        time.sleep(5)
        handle_election([])

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
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            thread = Thread(target = initiate_election, args = ())
            thread.deamon = True
            thread.start()
            run(app, host=vessel_list[str(node_id)], port=port)

        except Exception as e:
            print(e)
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
    traceback.print_exc()
    while True:
        time.sleep(60.)
