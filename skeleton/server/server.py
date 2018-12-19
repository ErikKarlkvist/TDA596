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
import copy

from bottle import Bottle, run, request, template, HTTPResponse
from threading import Thread
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    board = {}

    result_vote = []
    my_vector_r1 = dict()
    my_vectors_r2 = []

    on_tie = False

    traitor = False
    has_voted = False

    result = "YOU HAVE NOT VOTED"




# ------------------------------------------------------------------------------------------------------
    # BYZANTINE FUNCTIONS
    # ------------------------------------------------------------------------------------------------------

    #Compute byzantine votes for round 1, by trying to create
#a split decision.
#input: 
#   number of loyal nodes,
#   number of total nodes,
#   Decision on a tie: True or False 
#output:
#   A list with votes to send to the loyal nodes
#   in the form [True,False,True,.....]
    def compute_byzantine_vote_round1(no_loyal,no_total,on_tie):

        for i in range(0,no_loyal):
            if i%2==0:
                result_vote.append(not on_tie)
            else:
                result_vote.append(on_tie)
        return result_vote

#Compute byzantine votes for round 2, trying to swing the decision
#on different directions for different nodes.
#input: 
#   number of loyal nodes,
#   number of total nodes,
#   Decision on a tie: True or False
#output:
#   A list where every element is a vector that the 
#   byzantine node will send to every one of the loyal ones
#   in the form [[True,...],[False,...],...]
    def compute_byzantine_vote_round2(no_loyal,no_total,on_tie):
      
      result_vectors=[]
      for i in range(0,no_loyal):
        if i%2==0:
          result_vectors.append([on_tie]*no_total)
        else:
          result_vectors.append([not on_tie]*no_total)
      return result_vectors

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


    def add_to_vector(action, node_id):
        global my_vector_r1, vessel_list, result_vote, on_tie, node_id

        if(str(action) != "byzantine"):
            my_vector_r1[node_id] = action

        if(traitor): #if this node is a traitor, and the other generals has sent their values
            if(len(my_vector_r1) >= len(vessel_list)-1): #can only handle one traitor
                no_loyal = len(my_vector_r1)
                no_total = len(vessel_list)

                action = calculate_action_to_take(my_vector_r1) #sets global on_tie
                print("ON TIE: " + str(on_tie))

                print("Traitor vector: " + str(my_vector_r1))

                result_vote = compute_byzantine_vote_round1(no_loyal, no_total, on_tie)
                print("Result vote: " + str(result_vote))
                for i, val in enumerate(result_vote):
                    vessel = i + 1
                    if vessel == node_id:
                        vessel = vessel + 1
                    contact_vessel("10.1.0."+str(vessel), "/propagate/"+str(val), None, 'POST')


        elif(len(my_vector_r1) >= len(vessel_list)):
            print("FIRST ROUND MY LIST: " + str(my_vector_r1))
            action = calculate_action_to_take(my_vector_r1)
            print("WHAT ACTION AFTER ROUND 1: " + str(action))
            send_vector(my_vector_r1)

    def calculate_action_to_take(vector):
        global on_tie
        tcount = 0
        fcount = 0
        for key,el in my_vector_r1.iteritems():
            if el:
                tcount = tcount + 1
            else:
                fcount = fcount + 1
        if tcount == fcount:
            on_tie = True
        return tcount > fcount

    def calculate_result_for_loyal(vectors):
        global result
        newlist = copy.deepcopy(vectors)
        result = []
        length = len(newlist[0])

        while(len(newlist[len(newlist)-1]) > 0):
            tcount = 0
            for i, l in enumerate(newlist):
                print(l[0])
                if l[0]:
                    tcount = tcount + 1
                del l[0]
            if tcount > length - tcount:
                result.append(True)
            else:
                result.append(False)

        print("RESULT FOR LOYAL: " + str(result))
        action = calculate_action_to_take(result)
        if action:
            result = "ATTACK"
        else:
            result= "RETREAT"
        print("ACTION TO TAKE ROUND 2" + str(action))



       #for i, (e1, e2, e3, e4) in enumerate(zip(vector1, vector2, vector3, vector4)): #kolla om nåt element har en majoritet
         #   if()

    def send_vector(vector):
        global node_id
        print("Vektorn som skickas till de andra: "+ str(json.dumps(vector)))
        t = Thread(target = propagate_to_vessels, args = ('/propagate/vector/' + str(node_id), json.dumps(vector), 'POST'))
        t.deamon = True
        t.start()

    def reset(): #reset values so that a new voting can begin
        global has_voted, my_vector_r1, my_vectors_r2, on_tie, traitor

        my_vector_r1 = dict()
        my_vectors_r2 = []

        on_tie = False

        traitor = False
        has_voted = False
    #-----------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.get('/vote/result')
    def get_result():
        global result
        body = request.body.read()
        print("request: "+ str(body))
        return result

   # @app.get('/board')
    #def get


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
    @app.post('/vote/attack/')
    def client_attack_received():
        global has_voted, result, node_id
        if not has_voted:
            has_voted = True
            attack = request.forms.get('Attack') # ATTACK = TRUE
            t = Thread(target = propagate_to_vessels, args = ("/propagate/True/" + str(node_id), None, 'POST'))
            t.deamon = True
            t.start()
            add_to_vector(True, str(node_id))
            result = "WAITING FOR OTHERS TO VOTE"
            #body = request.body.read()
            #requestForm = request.forms
            print("Attack: " + str(attack))
         
    @app.post('/vote/retreat/')
    def client_retreat_received(element_id): # RETREAT = FALSE
        global has_voted, result, node_id
        if not has_voted:
            has_voted = True
            retreat = request.forms.get('Retreat')
            print("Retreat: " + str(retreat))
            result = "WAITING FOR OTHERS TO VOTE"
            t = Thread(target = propagate_to_vessels, args = ("/propagate/False/" + str(node_id), None, 'POST'))
            t.deamon = True
            t.start()
            add_to_vector(False, str(node_id))

    @app.post('/vote/byzantine')
    def client_byzantine_received():
        global no_total, no_loyal, traitor, has_voted, result, node_id
        if not has_voted:
            has_voted = True
            traitor = True
            result = "TRAITOR!"
            add_to_vector("byzantine", str(node_id))

    @app.post('/propagate/<action>/<element_id>')
    def propagation_received(action, element_id):
        global no_loyal, no_total, on_tie
        val = False
        if str(action) == "True":
            val = True
        add_to_vector(val, element_id)
        print("ACTION PROPAGATED: " + str(val))

    @app.post('/propagate/vector/<element_id>')
    def vector_received(element_id):
        global my_vectors_r2, my_vector_r1, vessel_list, node_id

        results_vectors = []

        my_vectors_r2.append(json.loads(request.body.read())) #add vector to list
        

        if(len(my_vectors_r2)==len(vessel_list)-1):
            if traitor:
                no_loyal = len(my_vector_r1)
                no_total = len(vessel_list) 
                print("NO TOTAL" + str(no_total))
                print("NO LOYAR" + str(no_loyal))
                result_vectors = compute_byzantine_vote_round2(no_loyal, no_total, on_tie)
                print("RESULT VECTORS: " + str(result_vectors))
                for i, val in enumerate(result_vectors):
                    vessel = i + 1
                    if vessel == node_id:
                        vessel = vessel + 1
                    contact_vessel("10.1.0."+str(vessel), "/propagate/vector/" + str(node_id), json.dumps(val), 'POST')
                reset()
            else: 
                my_vectors_r2.append(my_vector_r1)
                print("VECTOR RECEIVED AFTER ROUND 2: " + str(my_vectors_r2))
                calculate_result_for_loyal(my_vectors_r2)
                reset()
                
            
               




        
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
        for i in range(1, args.nbv+1):
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