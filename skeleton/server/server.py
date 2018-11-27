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
from random import randint
import time
from threading import Thread

from bottle import Bottle, run, request, template, HTTPResponse
from threading import Thread
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {}
    leader = -1
    randomID = -1

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

        success = False
        last_node = int(node_id)
        while(not success): 
            
            ip = '10.1.0.1'
            if last_node < len(vessel_list):
                last_node = last_node + 1
                ip = '10.1.0.'+str(last_node)

            success = contact_vessel(ip, path, payload, req)


    # --------------------------------------------------------------------------
    # ELECTION HANDLING
    # --------------------------------------------------------------------------

    def initiate_election():
        global randomID, node_id
        time.sleep(5)
        randomID = randint(len(vessel_list)+1,1000) #gives every vessel a random ID
        elecDict = {
            's': str(node_id), #start node. never changes
            'h': str(node_id), #highhest so far (myself)
            'v': str(randomID) #value of highets
        } #Everyone starts with an empty dictionary

        thread = Thread(target = propagate_to_next_vessel, args = ('/election/circulate/', json.dumps(elecDict), 'POST'))
        thread.deamon = True
        thread.start()
        

    def handle_election(elecDict):
        global node_id, randomID, leader

        if str(node_id) == elecDict['s']: #If a vessel has found itself -> It's time for leader election
            print("FOUND MYSELF: " + str(node_id))
            leader = elecDict['h']
            print("FOUND LEADER: " + str(leader))
            #handle_leader(elecDict)
        else: 
            if randomID > int(elecDict['v']) or (randomID == int(elecDict['v']) and int(elecDict['h']) > node_id): #Else just add your nodeID and randomID to the dictionary and continue
                print("Innan: " + str(elecDict))
                elecDict['h'] = node_id
                elecDict['v'] = randomID
                print("Efter: " + str(elecDict))

            thread = Thread(target = propagate_to_next_vessel, args = ('/election/circulate/', json.dumps(elecDict), 'POST'))
            thread.deamon = True
            thread.start()


        


    # --------------------------------------------------------------------------
    # LEADER HANDLES ACTION FROM OTHERS
    # --------------------------------------------------------------------------
    
    def leader_handle_element(action, entry, element_id): #The newfound leader sends the new messages to the other vessels
        global board

        if(action == "add"):
            element_id = len(board) + 1
            while(str(element_id) in board.keys()):  
                element_id = int(element_id) + 1
            add_new_element_to_store(element_id, entry)
        elif(action == "modify"): 
            modify_element_in_store(element_id, entry)
        else:
            delete_element_from_store(element_id)
        
        thread = Thread(target = propagate_to_vessels, args = ('/propagate/' + action + "/" + str(element_id), entry, 'POST'))
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
        global board, node_id, leader, randomID
        return template('server/index.tpl', leader="Leader ID: " + str(leader) + " My random number: " + str(randomID), board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems(), key = lambda x: x), members_name_string='knoph@student.chalmers.se & erikarlk@student.chalmers.se')

    @app.get('/board')
    def get_board():
        global board, node_id, randomID
        print(board)
        return template('server/boardcontents_template.tpl', leader="Leader ID: " + str(leader) + " My random number: " + str(randomID), board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems(), key = lambda x: x))
    # ------------------------------------------------------------------------------------------------------

    @app.post('/board')
    def client_add_received():

        global board, node_id, leader
        try:
            new_entry = request.forms.get('entry')
            if(node_id != leader):
                thread = Thread(target=contact_vessel, args=('10.1.0.'+ str(leader), "/leader/add/0", new_entry, 'POST'))
                thread.deamon = True
                thread.start()
            else:
                leader_handle_element("add", new_entry, -1)

            return "Latest entry: " + new_entry # Returning true gives a weird error so we return a describing string instead

        except Exception as e:
            print(e)
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):

        global board, node_id, leader

        action = ""  # action that determines modify or delete to be sent to propagate_to_vessels()

        # used 'forms' to get the values of entry and delete
        entryStr = request.forms.get('entry')
        deleteStr = request.forms.get('delete')

        try:
            if(deleteStr == "1"):
                action = "delete"
            elif(deleteStr == "0"):
                action = "modify"

            if(node_id != leader): 
                thread = Thread(target=contact_vessel, args=('10.1.0.'+ str(leader), "/leader/"+action+"/"+str(element_id), entryStr, 'POST'))
                thread.deamon = True
                thread.start()
            else:
                leader_handle_element(action, entryStr, element_id) 


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
        prev_elecDict = json.loads(body)
        handle_election(prev_elecDict)

    @app.post('/leader/<action>/<element_id>')
    def leader_propagation_recieved(action, element_id):
        entry = request.body.read()
        leader_handle_element(action, entry, element_id)

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
