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
    my_vector_r1 = []
    my_vectors_r2 = []

    no_loyal = 0
    no_total = 0
    on_tie = False

    traitor = False




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

        global result_vote

        for i in range(0,no_total):
            if i%2==0:
                result_vote.append(str(not on_tie))
            else:
                result_vote.append(str(on_tie))
        return result_vote

#Compute byzantine votes for round 2, trying to swing the decision
#on different directions for different nodes.
#input: 
#   number of loyal nodes,
#   number of total nodes,
#   Decision on a tie: True or False
#output:
#   A list where every element is a the vector that the 
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


    def add_to_vector(action):
        global my_vector_r1, vessel_list, result_vote, no_loyal, no_total, on_tie

        if(str(action) != "byzantine"):
            my_vector_r1.append(action)

        if(traitor): #if this node is a traitor, and the other generals has sent their values
            if(len(my_vector_r1) >= len(vessel_list)-1):
                no_loyal = len(my_vector_r1)
                no_total = len(vessel_list)
                tcount = 0
                fcount = 0
                myVote = "True"

                for i,el in enumerate(my_vector_r1):
                    if el:
                        tcount = tcount + 1
                    else:
                        fcount = fcount + 1
                if tcount > fcount:
                    myVote = "False"
                if tcount == fcount:
                    on_tie = True
                print("Traitor vote: " + myVote)

                my_vector_r1.append(myVote)
                print("Traitor vector: " + str(my_vector_r1))
                t = Thread(target = propagate_to_vessels, args = ("/propagate/" + str(myVote), None, 'POST'))
                t.deamon = True
                t.start()

                my_vector_r1 = compute_byzantine_vote_round1(no_loyal, no_total, on_tie)
                send_vector(result_vote)

        elif(len(my_vector_r1) >= len(vessel_list)):
            send_vector(my_vector_r1)

    def calculate_result_for_loyal(vectors):

        newlist = copy.deepcopy(vectors)
        result = []
        length = len(newlist[0])

        while(len(newlist[len(newlist)-1]) > 0):
            tcount = 0
            for i, l in enumerate(newlist):
                if l[0] == "True":
                    tcount = tcount + 1
                del l[0]
            if tcount > length - tcount:
                result.append("True")
            else:
                result.append("False")

        print("RESULT FOR LOYAL: " + str(result))


       #for i, (e1, e2, e3, e4) in enumerate(zip(vector1, vector2, vector3, vector4)): #kolla om nåt element har en majoritet
         #   if()

    def send_vector(vector):
        print("HÄR ÄR DEN: "+ str(json.dumps(vector)))
        t = Thread(target = propagate_to_vessels, args = ('/propagate/vector', json.dumps(vector), 'POST'))
        t.deamon = True
        t.start()

    #-----------------------------------------------------------------

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.get('/vote/result')
    def get_result():
        body = request.body.read()
        print("request: "+ str(body))

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
    @app.post('/vote/attack')
    def client_attack_received():
        attack = request.forms.get('Attack') # ATTACK = TRUE
        t = Thread(target = propagate_to_vessels, args = ("/propagate/True", None, 'POST'))
        t.deamon = True
        t.start()
        add_to_vector("True")
        #body = request.body.read()
        #requestForm = request.forms
        print("Attack: " + str(attack))
         

    @app.post('/vote/retreat')
    def client_retreat_received(): # RETREAT = FALSE
        retreat = request.forms.get('Retreat')
        print("Retreat: " + str(retreat))

        t = Thread(target = propagate_to_vessels, args = ("/propagate/False", None, 'POST'))
        t.deamon = True
        t.start()
        add_to_vector("False")
        
        
        

    @app.post('/vote/byzantine')
    def client_byzantine_received():
        global no_total, no_loyal, traitor
        traitor = True
        add_to_vector("byzantine")

    

    @app.post('/propagate/<action>')
    def propagation_received(action):
        global no_loyal, no_total, on_tie

        add_to_vector(action)
        print("ACTION PROPAGATED: " + str(action))

    @app.post('/propagate/vector')
    def vector_received():
        global my_vectors_r2, my_vector_r1
        
        results_vectors = []

        my_vectors_r2.append(json.loads(request.body.read())) #add vector to list

        if(!traitor):
            if(len(my_vectors_r2)==len(vessel_list)-1):
                my_vectors_r2.append(my_vector_r1)
                calculate_result_for_loyal(my_vectors_r2)
                print("VECTOR RECEIVED AFTER method: " + str(my_vectors_r2))
        else:
            results_vectors = compute_byzantine_vote_round2(no_total, no_loyal, on_tie)
           




        
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