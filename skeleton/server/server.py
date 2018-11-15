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

from bottle import Bottle, run, request, template
from threading import Thread
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {}



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
        print board
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=sorted(board.iteritems()))
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        
        global board
        try:
            new_entry = request.forms.get('entry')
            element_id = int(round(time.time()*1000000))
            #generate_id()
            add_new_element_to_store(element_id, new_entry) # you might want to change None here
            thread = Thread(target = propagate_to_vessels, args = ("/propagate/add/"+str(element_id), new_entry, 'POST'))
            thread.deamon = True
            thread.start()
            return "Latest entry: " + new_entry #Returning true gives a weird error so we return a describing string instead

        except Exception as e:
            print e
        return False

    @app.post('/board/<element_id:int>/')
    def client_action_received(element_id):

        global board, node_id

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
        

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):

        entry = request.body.read()

        if(action == "delete"):
            return delete_element_from_store(element_id)

        if(action == "modify"):
            return modify_element_in_store(element_id, entry)

        if(action == "add"):
            return add_new_element_to_store(element_id, entry)

    
    def generate_id():
        global board
        id = 0
        rs = (len(vessel_list)+1) # A start that is higher than the amount of vessels to avoid collisions
        re = 10000001 #random end
        if(len(board) == 0): #if board has length 0, just set random number
            id = random.randint(rs,re)
        else:
            id = board.keys()[0] #access first key in board just to have a key that already exist in while loop
            while(id in board): #if id is in board, retry until it's not
                id = random.randint(rs,re)
        return id
        
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