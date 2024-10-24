from flask import Flask, request, jsonify, render_template
from web3 import Web3
import json
import random
import hashlib
import time

app = Flask(__name__)

# Web3 setup
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545", request_kwargs={'timeout': 500}))
contract_address = Web3.to_checksum_address('0x73Dd3842730b975613fB78AA8f6ad25f260a141a')  # Replace with your deployed contract address

# Load the contract ABI
with open('e-transcript/build/contracts/SchnorrBatchVerification.json') as f:
    contract_json = json.load(f)
    contract_abi = contract_json['abi']

contract = w3.eth.contract(address=contract_address, abi=contract_abi)


@app.route('/', methods=['GET'])
def batch_ver_page():
    # Render the HTML form page for batch verification
    return render_template('batch_ver.html')

@app.route('/store', methods=['GET'])
def store_did_page():
    # Render the HTML form page for batch verification
    return render_template('store_did.html')

@app.route('/store_did_to_index', methods=['POST'])
def store_did_to_index():
    try:
        # Load the ipfs.json file to get DID and index information
        with open('ipfs.json', 'r') as f:
            ipfs_data = json.load(f)

        # Loop through each student's DID and index
        for index, student_data in ipfs_data.items():
            student_did = student_data['student_did']
            student_index = int(index)  # Convert index from string to integer

            # Call the smart contract function to store DID and index
            tx_hash = contract.functions.storeDidToIndex(student_did, student_index).transact({
                'from': w3.eth.accounts[4], 'gas': 200000000
            })
            # Wait for the transaction to be mined
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Stored DID: {student_did} with index: {student_index} on the blockchain")

        return jsonify({
            "status": "success",
            "message": "All DIDs and indices have been stored on the blockchain"
        })

    except Exception as e:
        return jsonify({
            "status": "failed",
            "message": str(e)
        })

# Static variables for Schnorr proof
G = 2  # Generator
P = 23  # Prime modulus

@app.route('/batch_verify', methods=['POST'])
def batch_verify_from_form():
    try:
        # Get loop count from the form input
        loop_count = int(request.form['loop_count'])
        
        # Load the necessary data from JSON files
        with open('batch_verification_payload.json', 'r') as f:
            students_data = json.load(f)['students']

        with open('token.json', 'r') as f:
            token_data = json.load(f)

        with open('ipfs.json', 'r') as f:
            ipfs_data = json.load(f)

        valid_students = []
        total_gas_used = 0  # Initialize total gas counter
        start_time = time.time()

        # Since there's only 1 student data, use the first student repeatedly
        student = students_data[0]

        for i in range(loop_count):
            student_did = student['student_did']
            student_email = student['email']
            
            # Log the student DID for debugging
            print(f"Starting verification for student_did={student_did}, student_email={student_email}")
            
            # Get the hashed VC from the IPFS data for this student
            ipfs_vc = ipfs_data.get("0", {}).get('hashed_vc')
            print(f"Retrieved ipfs_vc: {ipfs_vc}")

            if not ipfs_vc:
                print(f"Error: No hashed VC found for student {student_did}")
                continue

            # Perform Schnorr proof and VC verification for each iteration
            hashed_email = hashlib.sha256(student_email.encode()).hexdigest()
            r = random.randint(1, P-1)  # Random integer r in the range (1, P-1)
            R = pow(G, r, P)  # Calculate R = g^r mod P

            # Get challenge from the contract
            challenge = contract.functions.getChallenge(R).call()

            # Hash student's email to create the secret
            hashed_secret = int(hashlib.sha256(student_email.encode()).hexdigest(), 16) % P

            # Calculate s = (r + challenge * hashed_secret) mod (P-1)
            s = (r + challenge * hashed_secret) % (P-1)

            # Get employer hashed email from the token file
            employer_hashed_email = token_data['0']['acl']['employer_hashed_email']
            print(f"Employer hashed email: {employer_hashed_email}")

            # Log values to check
            print(f"R: {R}, s: {s}, G: {G}, P: {P}, challenge: {challenge}, employer_hashed_email: {employer_hashed_email}")

            # Call the unified verification function on the blockchain (Schnorr + VC verification)
            tx_hash = contract.functions.verify(
                R, s, G, P, challenge, employer_hashed_email,
                token_data['0']['verifiablePresentation']['verifiableCredential'][0]['hash'], 
                student_did, ipfs_vc
            ).transact({'from': w3.eth.accounts[3], 'gas': 200000000})

            # Wait for the transaction receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            # Log if the transaction succeeded or failed
            if receipt['status'] == 1:
                print(f"Transaction succeeded for student_did={student_did}")
            else:
                print(f"Transaction failed for student_did={student_did}, iteration={i + 1}. Gas used: {receipt['gasUsed']}")


            # Log the gas used for each iteration
            print(f"Gas used for iteration {i+1}: {receipt['gasUsed']}")
            total_gas_used += receipt['gasUsed']

        # Measure the total time taken for the batch verification process
        verification_time = time.time() - start_time

        # Render the results in the HTML page
        return render_template('batch_result.html', 
                       valid_students=valid_students, 
                       verification_time=verification_time, 
                       loop_count=loop_count,
                       total_gas_used=total_gas_used)

    except Exception as e:
        return jsonify({"status": "failed", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
