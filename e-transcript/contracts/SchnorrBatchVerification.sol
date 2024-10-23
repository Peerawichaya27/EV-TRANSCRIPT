// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SchnorrBatchVerification {

    // Mapping to store whether the Schnorr proof has been verified for a student DID
    mapping(string => bool) public schnorrProofVerified;
    
    // Mapping to store the index associated with a student's DID
    mapping(string => uint256) public didToIndex;

    // Event to emit debug values for LHS, RHS, R, and s
    event DebugValues(uint256 lhs, uint256 rhs, uint256 R, uint256 s, uint256 g_cx, uint256 x);

    // Store the index associated with a student's DID
    function storeDidToIndex(string memory studentDid, uint256 index) public {
        didToIndex[studentDid] = index;
    }

    // Retrieve the index associated with a student's DID
    function getIndexByDid(string memory studentDid) public view returns (uint256) {
        return didToIndex[studentDid];
    }

    // Check if Schnorr proof has been verified for a student's DID
    function hasVerifiedSchnorrProof(string memory studentDid) public view returns (bool) {
        return schnorrProofVerified[studentDid];
    }

    // Generate a challenge value using the value of R and current block timestamp
    function getChallenge(uint256 R) public view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(R, block.timestamp))) % 23;  // Example modulus 23
    }

    // Schnorr proof verification function
    function verifySchnorrProof(
        uint256 R, 
        uint256 s, 
        uint256 g, 
        uint256 p, 
        uint256 c, 
        string memory employerHashedEmail
    ) public returns (bool) {
        // Calculate LHS: g^s mod p
        uint256 lhs = modExp(g, s, p);
        
        // Calculate RHS: (R * g^(c * x)) mod p
        uint256 rhs = calculateRHS(R, g, c, employerHashedEmail, p);
        
        // Emit debug values for LHS, RHS, R, and s
        emit DebugValues(lhs, rhs, R, s, 0, 0);

        // Compare LHS and RHS
        require(lhs == rhs, "Schnorr proof failed");

        return true;
    }

    // Function to verify hashed Verifiable Credentials (VC)
    function verifyHashedVC(
        string memory hashedVCFromVP, 
        string memory studentDid, 
        string memory ipfsHashedVC
    ) public view returns (bool) {
        return keccak256(abi.encodePacked(hashedVCFromVP)) == keccak256(abi.encodePacked(ipfsHashedVC));
    }

    // Unified verification function that verifies both Schnorr proof and hashed VC
    function verify(
        uint256 R, 
        uint256 s, 
        uint256 g, 
        uint256 p, 
        uint256 c, 
        string memory employerHashedEmail, 
        string memory hashedVCFromVP, 
        string memory studentDid, 
        string memory ipfsHashedVC
    ) public returns (bool) {
        // If the Schnorr proof hasn't been verified yet, verify it
        if (!schnorrProofVerified[studentDid]) {
            bool schnorrResult = verifySchnorrProof(R, s, g, p, c, employerHashedEmail);
            require(schnorrResult, "Schnorr proof verification failed.");
            
            // Mark the Schnorr proof as verified
            schnorrProofVerified[studentDid] = true;
        }
        
        // Verify the hashed VC from the Verifiable Presentation
        bool vcVerified = verifyHashedVC(hashedVCFromVP, studentDid, ipfsHashedVC);
        require(vcVerified, "Hashed VC verification failed.");

        return true;
    }

    // Modular exponentiation function to compute base^exp % mod
    function modExp(uint256 base, uint256 exp, uint256 mod) internal pure returns (uint256) {
        uint256 result = 1;
        while (exp > 0) {
            if (exp % 2 == 1) {
                result = (result * base) % mod;
            }
            base = (base * base) % mod;
            exp /= 2;
        }
        return result;
    }

    // Calculate RHS = (R * g^(c * x)) mod p
    function calculateRHS(
        uint256 R, 
        uint256 g, 
        uint256 c, 
        string memory employerHashedEmail, 
        uint256 p
    ) internal returns (uint256) {
        // First calculate x = hash(employerHashedEmail)
        uint256 x = uint256(keccak256(abi.encodePacked(employerHashedEmail)));

        // Then calculate g^(c * x) mod p
        uint256 g_cx = modExp(g, c * x, p);

        // Emit debug values for x and g^(c * x)
        emit DebugValues(0, 0, R, 0, g_cx, x);

        // Finally calculate RHS = (R * g^(c * x)) mod p
        return (R * g_cx) % p;
    }
}
